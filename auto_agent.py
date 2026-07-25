import os
import re
import time
import logging
import pytz
import random
from datetime import datetime
from dotenv import load_dotenv

from src.scraper.multi_source_fetcher import get_latest_army_news
from src.scraper.image_search import get_related_image
from src.analyzer.llm_analyzer import generate_content_from_article, generate_facebook_caption
from src.image_editor.image_processor import create_facebook_post
from src.facebook.facebook_publisher import upload_to_facebook
from src.discord.discord_reporter import send_discord_report

import requests
import shutil
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_original_image(url, output_path):
    """Downloads the image as-is (in its original quality) without any editing or processing."""
    try:
        if url.startswith("http"):
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
            logging.info(f"Downloaded original image to {output_path}")
            return output_path
        else:
            shutil.copy(url, output_path)
            logging.info(f"Copied original local image to {output_path}")
            return output_path
    except Exception as e:
        logging.error(f"Error downloading original image from {url}: {e}")
        return None

def normalize_title(title):
    """Normalize title for comparison by removing non-alphanumeric chars and lowercasing."""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def is_trend_processed(trend):
    """Check if the trend has already been processed today."""
    if not os.path.exists("output/processed_news.txt"):
        return False
        
    norm_trend = normalize_title(trend)
    
    with open("output/processed_news.txt", "r", encoding="utf-8") as f:
        processed = f.read().splitlines()
        
    for p in processed:
        norm_p = normalize_title(p)
        if norm_p == norm_trend or (len(norm_p) > 15 and norm_p in norm_trend) or (len(norm_trend) > 15 and norm_trend in norm_p):
            return True
            
    return False

def save_processed_trend(trend_title):
    os.makedirs("output", exist_ok=True)
    with open("output/processed_news.txt", "a", encoding="utf-8") as f:
        f.write(f"{trend_title}\n")

def job():
    logging.info("Starting automated job for American Army News Agent...")
    
    # Check feeds for articles up to 24 hours old so we have choices
    news_items = get_latest_army_news(max_age_hours=24)
    if not news_items:
        logging.info("No fresh articles found.")
        return

    for item in news_items:
        title = item["title"]
        if is_trend_processed(title):
            continue
            
        logging.info(f"Processing new article: {title}")
        
        image_url = item["image_url"]
        description = item.get("description", "")
        source_url = item.get("link", "")
        source_name = item.get("source", "NEWS")
        
        # 1. Ensure only the original news article thumbnail is used
        if not image_url:
            logging.warning(f"No original thumbnail image found for: {title}. Skipping article to preserve exact thumbnail rule.")
            continue
        image_url_2 = None
        
        os.makedirs("output", exist_ok=True)
        generation_time = datetime.now(pytz.timezone('America/New_York')).strftime('%Y%m%d_%H%M%S')
        post_id = f"{generation_time}_{int(time.time())}"
        
        # 2. Image Content & Style
        ai_data = generate_content_from_article(title, description)
        headline = ai_data.get("headline", title)
        hook_text = ai_data.get("hook_text", description)
        safety_flags = ai_data.get("safety_flags", [])
        
        if safety_flags:
            logging.warning(f"Skipping article due to safety flags: {safety_flags}")
            continue
            
        logging.info(f"Headline: {headline}")
        
        # 3. Image Creation
        if isinstance(image_url, list):
            processed_img_path = []
            for idx, img_u in enumerate(image_url):
                if idx == 0:
                    poster_path = f"output/post_{post_id}_{idx}.jpg"
                    single_path = create_facebook_post(
                        image_url=img_u, 
                        image_url_2=image_url_2,
                        headline=headline,
                        hook_text=hook_text,
                        source_name=source_name,
                        output_path=poster_path,
                        logo_path="assets/logo/logo.png"
                    )
                else:
                    ext = ".jpg"
                    try:
                        parsed_url = urlparse(img_u)
                        _, url_ext = os.path.splitext(parsed_url.path)
                        if url_ext.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                            ext = url_ext.lower()
                    except Exception:
                        pass
                    poster_path = f"output/post_{post_id}_{idx}{ext}"
                    single_path = download_original_image(img_u, poster_path)
                
                if single_path:
                    processed_img_path.append(single_path)
            if not processed_img_path:
                logging.error(f"Failed to create any images for {title}.")
                continue
        else:
            poster_path = f"output/post_{post_id}.jpg"
            processed_img_path = create_facebook_post(
                image_url=image_url, 
                image_url_2=image_url_2,
                headline=headline,
                hook_text=hook_text,
                source_name=source_name,
                output_path=poster_path,
                logo_path="assets/logo/logo.png"
            )
            if not processed_img_path:
                logging.error(f"Failed to create image for {title}.")
                continue
            
        # 4. Facebook Caption
        try:
            facebook_caption = generate_facebook_caption(title)
        except Exception as e:
            logging.warning("LLM caption generation failed. Using fallback template.")
            facebook_caption = f"🇺🇸 American Army Update! 🇺🇸\n\n{title}\n\nStay tuned for more updates! 👇\n#USArmy #MilitaryNews #Pentagon #Defense #AmericanArmyNews"

        # Check if dry-run mode (Facebook credentials not supplied or are placeholders)
        fb_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        is_dry_run = not fb_token or fb_token == "your_facebook_access_token"
        
        if is_dry_run:
            logging.info("--- DRY-RUN MODE ACTIVE ---")
            logging.info(f"Generated Image(s): {processed_img_path}")
            logging.info(f"Facebook Caption:\n{facebook_caption}")
            save_processed_trend(title)
            logging.info("Dry-run processed successfully.")
            break

        # 5. Human-like Delay before Upload (jitter)
        sleep_time = random.randint(30, 120)
        logging.info(f"Human-like Jitter: Waiting for {sleep_time} seconds before posting...")
        time.sleep(sleep_time)

        # 6. Upload to Facebook
        upload_success, fb_post_id = upload_to_facebook(processed_img_path, facebook_caption)
        
        # 7. Discord Report
        page_id = os.getenv("FACEBOOK_PAGE_ID", "1094922960379153")
        status_text = "Success" if upload_success else "Failed"
        post_url = f"https://www.facebook.com/{page_id}/posts/{fb_post_id}" if upload_success else "N/A"
        
        original_files_str = ", ".join(os.path.basename(p) for p in processed_img_path) if isinstance(processed_img_path, list) else os.path.basename(processed_img_path)
        
        repo_name = os.getenv("GITHUB_REPOSITORY", "Vikram-Bosak/american-army-news-agent")
        run_id = os.getenv("GITHUB_RUN_ID", "")
        server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        repo_url = f"{server_url}/{repo_name}"
        run_url = f"{repo_url}/actions/runs/{run_id}" if run_id else "N/A"

        report = f"""✅ American Army News Pipeline Run Completed
        
🇺🇸 Headline:
{headline}

📤 Facebook Upload Status: {status_text}

📝 Description:
{facebook_caption}

Original File: {original_files_str}

📦 GitHub Repository:
{repo_url}

📄 Workflow Run:
{run_url}

📘 Facebook Post URL:
{post_url}

📄 Source Article:
{source_url}
"""
        send_discord_report(processed_img_path, report)
        save_processed_trend(title)

        if upload_success:
            logging.info(f"Successfully processed and uploaded: {title}")
        else:
            logging.error(f"Failed to upload to Facebook: {fb_post_id}")
            
        break

if __name__ == "__main__":
    load_dotenv(override=True)
    job()

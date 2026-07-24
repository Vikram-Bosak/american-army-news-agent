import feedparser
import logging
import time
import os
import requests
import re
from urllib.parse import urlparse

def is_us_news_site(url):
    """
    Checks if a URL belongs to a US official military/government site or media distribution portal.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Strictly allow .mil, .gov, or dvidshub.net (official military media hub)
    if domain.endswith(".mil") or domain.endswith(".gov") or "dvidshub.net" in domain:
        return True
        
    return False

def get_og_image(url):
    """
    Fetches the article URL (decoding it if it's a Google News link) and extracts the OpenGraph image tag.
    """
    target_url = url
    if "news.google.com" in url:
        try:
            from googlenewsdecoder import new_decoderv1
            decoded_res = new_decoderv1(url)
            if decoded_res.get("status") and decoded_res.get("decoded_url"):
                target_url = decoded_res["decoded_url"]
                logging.info(f"Successfully decoded Google News URL to: {target_url}")
        except Exception as e:
            logging.warning(f"Failed to decode Google News link using googlenewsdecoder: {e}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        logging.info(f"Attempting to extract og:image from: {target_url}")
        r = requests.get(target_url, headers=headers, timeout=10)
        if r.status_code == 200:
            html = r.text
            match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not match:
                match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.IGNORECASE)
            if match:
                img_url = match.group(1)
                logging.info(f"Found og:image: {img_url}")
                return img_url
    except Exception as e:
        logging.warning(f"Failed to scrape og:image from {target_url}: {e}")
    return None

FEEDS = [
    "https://news.google.com/rss/search?q=%22American+Army%22+OR+%22US+Army%22+trending&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22American+Army%22+OR+%22US+Army%22+breaking&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22American+Army%22+OR+%22US+Army%22+latest&hl=en-US&gl=US&ceid=US:en"
]

def get_latest_army_news(max_age_hours=2):
    """
    Fetches the latest American Army & Military news from Google News RSS.
    Filters out news older than max_age_hours.
    Sorts by newest first.
    Returns a list of dictionaries with 'title', 'link', 'description', and 'image_url'.
    """
    news_items = []
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    # 1. Fetch from Nitter RSS Feeds (Twitter alternative for official accounts)
    nitter_instances = [
        "https://nitter.cz",
        "https://nitter.privacydev.net",
        "https://nitter.net"
    ]
    official_users = ["USArmy", "DeptofDefense", "I_Corps"]
    for user in official_users:
        for instance in nitter_instances:
            nitter_url = f"{instance}/{user}/rss"
            logging.info(f"Scanning official Twitter feed on Nitter: {nitter_url}")
            try:
                feed = feedparser.parse(nitter_url)
                if not feed.entries:
                    continue
                    
                user_found = False
                for entry in feed.entries:
                    pub_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = time.mktime(entry.published_parsed)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_time = time.mktime(entry.updated_parsed)
                    
                    if not pub_time:
                        continue
                    
                    age_seconds = current_time - pub_time
                    if age_seconds < 0 or age_seconds > max_age_seconds:
                        continue
                        
                    title = entry.title
                    # Convert Nitter link to standard Twitter URL
                    link = entry.link
                    if instance in link:
                        link = link.replace(instance, "https://twitter.com").replace("#m", "")
                        
                    description = getattr(entry, 'description', '')
                    
                    # Skip video/GIF tweets to only process high-res photos
                    desc_lower = description.lower()
                    if "video" in desc_lower or "gif" in desc_lower or ".mp4" in desc_lower:
                        continue
                    
                    # Extract image URLs from Nitter HTML description (if present)
                    image_urls = []
                    img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', description)
                    for img in img_matches:
                        if "/pic/media" in img:
                            media_path = img.split("/pic/media%2F")[-1]
                            import urllib.parse
                            media_path = urllib.parse.unquote(media_path)
                            image_urls.append(f"https://pbs.twimg.com/media/{media_path}")
                        elif img.startswith("http"):
                            image_urls.append(img)
                            
                    image_val = None
                    if len(image_urls) > 1:
                        image_val = image_urls
                    elif len(image_urls) == 1:
                        image_val = image_urls[0]
                            
                    # For Twitter, the title is usually the tweet text
                    news_items.append({
                        "title": title[:100] + "..." if len(title) > 100 else title,
                        "link": link,
                        "description": description,
                        "image_url": image_val,
                        "timestamp": pub_time,
                        "source": "TWITTER/NITTER"
                    })
                    user_found = True
                
                # If we successfully parsed from one working instance, move to the next user
                if user_found:
                    break
            except Exception as e:
                logging.error(f"Error fetching from Nitter instance {instance} for {user}: {e}")


    # 2. Fetch from Google News RSS Feeds
    for rss_url in FEEDS:
        logging.info(f"Scanning feed: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                pub_time = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = time.mktime(entry.published_parsed)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_time = time.mktime(entry.updated_parsed)
                
                if not pub_time:
                    continue
                
                age_seconds = current_time - pub_time
                if age_seconds < 0 or age_seconds > max_age_seconds:
                    continue
                    
                title = entry.title
                link = entry.link
                description = getattr(entry, 'description', '')
                
                # Check for relevant terms to filter out noise (strictly US/American Army)
                title_lower = title.lower()
                if not any(x in title_lower for x in ["us army", "u.s. army", "american army", "usarmy"]):
                    continue
                    
                image_url = None
                
                # 1. Try media_content
                if hasattr(entry, 'media_content'):
                    max_width = 0
                    for media in entry.media_content:
                        if media.get('medium') == 'image':
                            width = int(media.get('width', 0))
                            if width > max_width:
                                max_width = width
                                image_url = media.get('url')
                    if not image_url and len(entry.media_content) > 0:
                        image_url = entry.media_content[0].get('url')
                        
                # 2. Try media_thumbnail
                if not image_url and hasattr(entry, 'media_thumbnail'):
                    if len(entry.media_thumbnail) > 0:
                        image_url = entry.media_thumbnail[0].get('url')
                        
                # 3. Try enclosures
                if not image_url and hasattr(entry, 'enclosures'):
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image/'):
                            image_url = enc.get('href')
                            break
                
                # Decode Google News link to verify destination domain is US-centric
                target_url = link
                if "news.google.com" in link:
                    try:
                        from googlenewsdecoder import new_decoderv1
                        decoded_res = new_decoderv1(link)
                        if decoded_res.get("status") and decoded_res.get("decoded_url"):
                            target_url = decoded_res["decoded_url"]
                    except Exception:
                        pass
                
                if not is_us_news_site(target_url):
                    logging.info(f"Skipping non-US news site: {target_url}")
                    continue
                
                # 4. Try scraping og:image from decoded publisher URL
                if not image_url and target_url:
                    image_url = get_og_image(target_url)
                            
                # Note: Unlike entertainment news, Google News articles sometimes do not bundle the image URL inside the RSS XML entry.
                # In that case, we can still fetch the entry and rely on image search in auto_agent.py.
                news_items.append({
                    "title": title,
                    "link": target_url,
                    "description": description,
                    "image_url": image_url,
                    "timestamp": pub_time,
                    "source": "GOOGLE_NEWS"
                })
                    
        except Exception as e:
            logging.error(f"Error fetching {rss_url}: {e}")

    # Sort items by timestamp, newest first
    news_items.sort(key=lambda x: x['timestamp'], reverse=True)
    logging.info(f"Found {len(news_items)} fresh military articles (under {max_age_hours} hours old).")
    return news_items

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    news = get_latest_army_news(max_age_hours=24)
    logging.info(f"Test complete. Found {len(news)} items.")

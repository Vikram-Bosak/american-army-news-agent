import feedparser
import logging
import time
import os
import requests
import re

def get_og_image(url):
    """
    Fetches the article URL and extracts the OpenGraph image tag.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        logging.info(f"Attempting to extract og:image from: {url}")
        r = requests.get(url, headers=headers, timeout=10)
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
        logging.warning(f"Failed to scrape og:image from {url}: {e}")
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

    # 1. Fetch from Nitter RSS Feeds (Twitter alternative)
    nitter_instances = [
        "https://nitter.cz",
        "https://nitter.privacydev.net",
        "https://nitter.net"
    ]
    for instance in nitter_instances:
        nitter_url = f"{instance}/search/rss?q=%22American+Army%22+OR+%22US+Army%22+trending"
        logging.info(f"Scanning Nitter feed: {nitter_url}")
        try:
            feed = feedparser.parse(nitter_url)
            if not feed.entries:
                continue
                
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
                
                # Extract image URL from Nitter HTML description (if present)
                image_url = None
                img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', description)
                for img in img_matches:
                    if "/pic/media" in img:
                        # Convert proxy image to standard Twitter image
                        # Example: /pic/media%2FEv12345.jpg -> https://pbs.twimg.com/media/Ev12345.jpg
                        media_path = img.split("/pic/media%2F")[-1]
                        # unquote URL characters
                        import urllib.parse
                        media_path = urllib.parse.unquote(media_path)
                        image_url = f"https://pbs.twimg.com/media/{media_path}"
                        break
                    elif img.startswith("http"):
                        image_url = img
                        break
                        
                news_items.append({
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "link": link,
                    "description": description,
                    "image_url": image_url,
                    "timestamp": pub_time,
                    "source": "TWITTER/NITTER"
                })
            # If we successfully parsed from one instance, no need to query others to avoid rate limiting
            if news_items:
                break
        except Exception as e:
            logging.error(f"Error fetching from Nitter instance {instance}: {e}")


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
                
                # 4. Try scraping og:image from original article URL
                if not image_url and link:
                    image_url = get_og_image(link)
                            
                # Note: Unlike entertainment news, Google News articles sometimes do not bundle the image URL inside the RSS XML entry.
                # In that case, we can still fetch the entry and rely on image search in auto_agent.py.
                news_items.append({
                    "title": title,
                    "link": link,
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

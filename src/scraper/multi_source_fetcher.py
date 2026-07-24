import feedparser
import logging
import time
import os
import requests

FEEDS = [
    "https://news.google.com/rss/search?q=American+Army+OR+US+Army+OR+US+Military&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Pentagon+defense+news&hl=en-US&gl=US&ceid=US:en"
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

    # 1. Try Twitter (X) if credentials are provided (Stub/Placeholder/Integration)
    x_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if x_bearer_token:
        logging.info("Twitter API Credentials found. Attempting to fetch tweets...")
        try:
            # Simple fetch from Twitter API search endpoint
            search_url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {"Authorization": f"Bearer {x_bearer_token}"}
            params = {
                "query": "(\"American Army\" OR \"US Army\" OR \"US military\") -is:retweet has:media",
                "max_results": 10,
                "tweet.fields": "created_at,attachments",
                "expansions": "attachments.media_keys",
                "media.fields": "url,preview_image_url"
            }
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                media_map = {m["media_key"]: m.get("url") or m.get("preview_image_url") 
                             for m in data.get("includes", {}).get("media", [])}
                
                for t in tweets:
                    # Parse created_at
                    created_at_str = t.get("created_at")
                    # Convert RFC3339 string to timestamp
                    # example: 2026-07-24T05:28:30.000Z
                    import datetime
                    dt = datetime.datetime.strptime(created_at_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    pub_time = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
                    
                    age_seconds = current_time - pub_time
                    if 0 <= age_seconds <= max_age_seconds:
                        media_keys = t.get("attachments", {}).get("media_keys", [])
                        img_url = media_map.get(media_keys[0]) if media_keys else None
                        
                        news_items.append({
                            "title": t.get("text")[:100] + "...",
                            "link": f"https://twitter.com/twitter/status/{t.get('id')}",
                            "description": t.get("text"),
                            "image_url": img_url,
                            "timestamp": pub_time,
                            "source": "TWITTER"
                        })
            else:
                logging.warning(f"Twitter API request failed with status code {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"Error fetching from Twitter: {e}")

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
                
                # Check for relevant terms to filter out noise if needed
                title_lower = title.lower()
                if not any(x in title_lower for x in ["army", "military", "soldier", "pentagon", "defense", "troop", "armed forces"]):
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

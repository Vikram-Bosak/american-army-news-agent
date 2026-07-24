from duckduckgo_search import DDGS
import logging
import re
import requests
import urllib.parse

def get_bing_image(query, avoid_url=None):
    """
    Fallback method to search Bing Images for a related image.
    Does not suffer from DuckDuckGo's strict rate limits.
    """
    logging.info(f"Searching Bing Images for: '{query}'")
    try:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=10)
        urls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', r.text)
        if not urls:
            urls = re.findall(r'"murl"\s*:\s*"([^"]+)"', r.text)
            
        for u in urls:
            u_clean = urllib.parse.unquote(u.replace("\\", ""))
            if u_clean.startswith("http") and u_clean != avoid_url:
                u_lower = u_clean.lower()
                if any(x in u_lower for x in ["chart", "diagram", "psychrometric", "blueprint", "graph", "vector", "icon", "placeholder"]):
                    continue
                if "lookaside.fbsbx.com" in u_lower:
                    continue
                logging.info(f"Found related image on Bing: {u_clean}")
                return u_clean
    except Exception as e:
        logging.warning(f"Bing image search failed: {e}")
    return None

def get_related_image(keyword, avoid_url=None):
    """
    Searches for an image related to the keyword.
    Tries DuckDuckGo first, and falls back to Bing Images if rate-limited.
    """
    clean_keyword = re.sub(r"[‘’“”\"']", "", keyword)
    words = [w for w in clean_keyword.split() if w]
    stop_words = {"to", "joins", "star", "in", "for", "gets", "with", "from", "on", "at", "by", "of", "and", "a", "an", "the", "about", "set", "is", "are", "was", "were", "to", "star", "direct", "talks"}
    filtered_words = [w for w in words if w.lower() not in stop_words]
    # Restrict title keywords to 3 words and append "US Army" to guarantee the image features American Army soldiers or assets
    base_query = " ".join(filtered_words[:3]) if len(filtered_words) > 3 else " ".join(filtered_words)
    query = f"{base_query} US Army"
    
    logging.info(f"Searching for related image using query: '{query}'")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(
                query,
                region="wt-wt",
                safesearch="moderate",
                size="Large",
                max_results=10
            ))
            for res in results:
                img_url = res.get('image')
                if img_url and img_url != avoid_url:
                    img_url_lower = img_url.lower()
                    if any(x in img_url_lower for x in ["chart", "diagram", "psychrometric", "blueprint", "graph", "vector", "icon", "placeholder"]):
                        continue
                    if "lookaside.fbsbx.com" in img_url_lower:
                        continue
                    logging.info(f"Found related image on DDG: {img_url}")
                    return img_url
    except Exception as e:
        logging.warning(f"DuckDuckGo image search failed: {e}. Falling back to Bing Search...")
        
    return get_bing_image(query, avoid_url)

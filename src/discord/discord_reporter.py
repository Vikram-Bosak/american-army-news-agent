import os
import requests
import logging

def send_discord_report(photo_path, message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        logging.warning("DISCORD_WEBHOOK_URL missing. Skipping Discord report.")
        return None
        
    try:
        with open(photo_path, 'rb') as f:
            files = {
                'file': ('image.jpg', f, 'image/jpeg')
            }
            payload = {
                'content': message
            }
            response = requests.post(webhook_url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            logging.info("Discord report sent successfully.")
            return True
            
    except Exception as e:
        logging.error(f"Failed to send Discord report: {e}")
        return None

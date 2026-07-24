import os
import requests
import logging

def send_discord_report(photo_path, message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        logging.warning("DISCORD_WEBHOOK_URL missing. Skipping Discord report.")
        return None
        
    try:
        files = {}
        opened_files = []
        
        if isinstance(photo_path, list):
            for i, path in enumerate(photo_path):
                f = open(path, 'rb')
                opened_files.append(f)
                files[f'file{i}'] = (os.path.basename(path), f, 'image/jpeg')
        else:
            f = open(photo_path, 'rb')
            opened_files.append(f)
            files['file'] = (os.path.basename(photo_path), f, 'image/jpeg')
            
        payload = {
            'content': message
        }
        
        try:
            response = requests.post(webhook_url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            logging.info("Discord report sent successfully.")
            return True
        finally:
            for f in opened_files:
                f.close()
            
    except Exception as e:
        logging.error(f"Failed to send Discord report: {e}")
        return None


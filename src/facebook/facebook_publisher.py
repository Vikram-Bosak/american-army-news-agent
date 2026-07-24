import os
import requests
import logging

def upload_to_facebook(image_path, text_content):
    """
    Uploads the image and text to Facebook using the Graph API.
    """
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
    
    if not access_token:
        logging.error("FACEBOOK_ACCESS_TOKEN is missing. Cannot upload to Facebook.")
        return False, "FACEBOOK_ACCESS_TOKEN is missing"
        
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    
    try:
        with open(image_path, 'rb') as image_file:
            files = {
                'source': image_file
            }
            data = {
                'message': text_content,
                'access_token': access_token,
                'published': 'true'
            }
            
            logging.info(f"Uploading {image_path} to Facebook...")
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            post_id = result.get('post_id', result.get('id'))
            logging.info(f"Successfully uploaded to Facebook! Post ID: {post_id}")
            return True, post_id
            
    except Exception as e:
        error_msg = f"Failed to upload to Facebook: {e}"
        logging.error(error_msg)
        if 'response' in locals() and hasattr(response, 'text'):
            logging.error(f"Facebook API Response: {response.text}")
            error_msg += " " + response.text
        return False, error_msg

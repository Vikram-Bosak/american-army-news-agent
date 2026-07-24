import os
import requests
import logging
import json

def upload_multi_photos_to_facebook(image_paths, text_content):
    """
    Uploads multiple photos to Facebook as a single post.
    """
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
    
    if not access_token:
        logging.error("FACEBOOK_ACCESS_TOKEN is missing. Cannot upload to Facebook.")
        return False, "FACEBOOK_ACCESS_TOKEN is missing"
        
    photo_ids = []
    
    # 1. Upload each photo with published=false
    for path in image_paths:
        url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
        try:
            with open(path, 'rb') as image_file:
                files = {'source': image_file}
                data = {
                    'access_token': access_token,
                    'published': 'false'
                }
                logging.info(f"Uploading temporary photo {path}...")
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
                res_data = response.json()
                photo_id = res_data.get('id')
                if photo_id:
                    photo_ids.append(photo_id)
                    logging.info(f"Uploaded photo ID: {photo_id}")
        except Exception as e:
            logging.error(f"Failed to upload photo {path}: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                logging.error(f"Response: {response.text}")
                
    if not photo_ids:
        return False, "No photos were successfully uploaded"
        
    # 2. Publish a feed post attaching all uploaded photo IDs
    feed_url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    try:
        attached_media = [{"media_fbid": pid} for pid in photo_ids]
        data = {
            'message': text_content,
            'attached_media': json.dumps(attached_media),
            'access_token': access_token
        }
        logging.info("Creating multi-photo post on feed...")
        response = requests.post(feed_url, data=data)
        response.raise_for_status()
        result = response.json()
        post_id = result.get('id')
        logging.info(f"Successfully uploaded multi-photo post! Post ID: {post_id}")
        return True, post_id
    except Exception as e:
        error_msg = f"Failed to create feed post: {e}"
        logging.error(error_msg)
        if 'response' in locals() and hasattr(response, 'text'):
            logging.error(f"Response: {response.text}")
            error_msg += " " + response.text
        return False, error_msg

def upload_to_facebook(image_path, text_content):
    """
    Uploads the image (or list of images) and text to Facebook using the Graph API.
    """
    if isinstance(image_path, list):
        return upload_multi_photos_to_facebook(image_path, text_content)
        
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


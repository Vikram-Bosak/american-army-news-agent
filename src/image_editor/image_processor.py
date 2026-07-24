import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_font_downloaded(font_url, font_path):
    if not os.path.exists(font_path):
        try:
            r = requests.get(font_url)
            with open(font_path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logging.error(f"Failed to download font: {e}")

def get_font(name="anton", size=40):
    os.makedirs("assets/fonts", exist_ok=True)
    if name == "anton":
        font_path = "assets/fonts/Anton-Regular.ttf"
        font_url = "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
        if not os.path.exists(font_path) or os.path.getsize(font_path) < 10000:
            try:
                logging.info(f"Downloading {name} font from {font_url}...")
                r = requests.get(font_url)
                r.raise_for_status()
                with open(font_path, "wb") as f:
                    f.write(r.content)
            except Exception as e:
                logging.warning(f"Failed to download font: {e}")
        try:
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.warning(f"Failed to load downloaded font, falling back to Impact/Arial. Error: {e}")
            try:
                return ImageFont.truetype("impact.ttf", size)
            except Exception:
                try:
                    return ImageFont.truetype("arialbd.ttf", size)
                except Exception:
                    return ImageFont.load_default()
    elif name == "roboto":
        font_path = "assets/fonts/Roboto-Bold.ttf"
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    else:
        font_path = "assets/fonts/Roboto-Regular.ttf"
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
        
    if os.path.exists(font_path) and os.path.getsize(font_path) < 10000:
        os.remove(font_path)
        
    ensure_font_downloaded(font_url, font_path)
    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logging.warning(f"Failed to load downloaded font, falling back to Impact/Arial. Error: {e}")
        try:
            return ImageFont.truetype("impact.ttf", size)
        except Exception:
            try:
                return ImageFont.truetype("arialbd.ttf", size)
            except Exception:
                return ImageFont.load_default()

def center_crop(img, target_w, target_h):
    img_w, img_h = img.size
    ratio = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * ratio)
    new_h = int(img_h * ratio)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img_resized.crop((left, top, left + target_w, top + target_h))

def fetch_image(url):
    try:
        if url.startswith("http"):
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert('RGB')
        else:
            return Image.open(url).convert('RGB')
    except Exception as e:
        logging.error(f"Error downloading/opening image {url}: {e}")
        return None

def draw_gradient(image, top_y, bottom_y, color_start=(0,0,0,0), color_end=(0,0,0,255)):
    draw = ImageDraw.Draw(image, 'RGBA')
    height = bottom_y - top_y
    for i in range(height):
        ratio = i / height
        r = int(color_start[0] + ratio * (color_end[0] - color_start[0]))
        g = int(color_start[1] + ratio * (color_end[1] - color_start[1]))
        b = int(color_start[2] + ratio * (color_end[2] - color_start[2]))
        a = int(color_start[3] + ratio * (color_end[3] - color_start[3]))
        draw.line([(0, top_y + i), (image.width, top_y + i)], fill=(r,g,b,a))

def draw_circular_badge(base_img, flag_url_or_path, size=300, pos_x=70, pos_y=600):
    badge_img = fetch_image(flag_url_or_path)
    if not badge_img:
        badge_img = Image.new('RGB', (size, size), "#1F4E5B")
        
    badge_img.thumbnail((size, size), Image.Resampling.LANCZOS)
    square_img = Image.new('RGB', (size, size), "#000000")
    w, h = badge_img.size
    square_img.paste(badge_img, ((size - w) // 2, (size - h) // 2))
    badge_img = square_img
    
    mask = Image.new('L', (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size, size), fill=255)
    
    circular_badge = Image.new('RGBA', (size, size), (0,0,0,0))
    circular_badge.paste(badge_img.convert("RGBA"), (0, 0), mask)
    
    draw_border = ImageDraw.Draw(circular_badge)
    draw_border.ellipse((0, 0, size, size), outline="#FFFFFF", width=4)
    
    shadow_size = size + 30
    shadow = Image.new('RGBA', (shadow_size, shadow_size), (0,0,0,0))
    draw_shadow = ImageDraw.Draw(shadow)
    shadow_offset = 15
    draw_shadow.ellipse((0, 0, shadow_size, shadow_size), fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    
    base_img.paste(shadow, (pos_x - shadow_offset, pos_y - shadow_offset), shadow)
    base_img.paste(circular_badge, (pos_x, pos_y), circular_badge)

def render_multicolor_text_centered(draw, text, y_pos, font, max_width, img_width, dry_run=False):
    tokens = []
    in_highlight = False
    highlight_idx = -1
    for word in text.split():
        if "*" in word and word.find("*") < len(word) / 2:
            if not in_highlight:
                in_highlight = True
                highlight_idx += 1
            
        ends_with = "*" in word[len(word)//2:] and len(word) > 1
        clean_word = word.replace("*", "")
        tokens.append({"text": clean_word, "highlight": in_highlight, "color_idx": highlight_idx})
        if ends_with:
            in_highlight = False

    lines = []
    current_line = []
    
    def get_word_width(word):
        try:
            bbox_word = draw.textbbox((0, 0), word, font=font)
            return bbox_word[2] - bbox_word[0]
        except AttributeError:
            return draw.textsize(word, font=font)[0]
        
    try:
        space_w = draw.textbbox((0, 0), " ", font=font)[2] - draw.textbbox((0, 0), " ", font=font)[0]
    except AttributeError:
        space_w = draw.textsize(" ", font=font)[0]
        
    def get_line_width(line_tokens):
        if not line_tokens:
            return 0
        total = sum(get_word_width(t["text"]) for t in line_tokens)
        total += space_w * (len(line_tokens) - 1)
        return total

    for token in tokens:
        current_line.append(token)
        if get_line_width(current_line) > max_width:
            current_line.pop()
            lines.append(current_line)
            current_line = [token]
    if current_line:
        lines.append(current_line)
        
    try:
        ascent, descent = font.getmetrics()
        line_height = ascent + descent
    except Exception:
        try:
            bbox_A = draw.textbbox((0, 0), "hg", font=font)
            line_height = bbox_A[3] - bbox_A[1]
        except AttributeError:
            line_height = draw.textsize("hg", font=font)[1]
    
    actual_line_height = line_height * 0.9
    total_height = len(lines) * actual_line_height
    
    if dry_run:
        return total_height
    
    for line_tokens in lines:
        line_width = get_line_width(line_tokens)
        x_pos = (img_width - line_width) // 2
        
        for token in line_tokens:
            clean_word = token["text"]
            if token["highlight"]:
                # Premium military-aligned highlights (Yellow-Gold, Red, Cyan, Green)
                HIGHLIGHT_COLORS = ["#FFCC00", "#FF3B30", "#30B0C7", "#34C759"]
                color = HIGHLIGHT_COLORS[token["color_idx"] % len(HIGHLIGHT_COLORS)]
            else:
                color = "#FFFFFF"
            
            draw.text((x_pos, y_pos), clean_word, font=font, fill=color)
            x_pos += get_word_width(clean_word) + space_w
            
        y_pos += actual_line_height
        
    return y_pos

def create_facebook_post(image_url, image_url_2, headline, source_name="NEWS", output_path="output.jpg", logo_path="assets/logo/logo.png", hook_text="", circle_image_url=None):
    if not circle_image_url and image_url_2:
        circle_image_url = image_url_2
        image_url_2 = None
        
    base_width, base_height = 1080, 1350
    bg_color = "#0B0C10"
    
    base_img = Image.new('RGB', (base_width, base_height), color=bg_color)
    
    img1 = fetch_image(image_url) if image_url else None
    img2 = fetch_image(image_url_2) if image_url_2 else None
    
    def apply_safety(img):
        if not img: return None
        img = ImageOps.mirror(img)
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(1.02)
        
    img1 = apply_safety(img1)
    img2 = apply_safety(img2)
    
    if img1 and img2:
        w1, w2 = 540, 540
        img1_cropped = center_crop(img1, w1, base_height)
        img2_cropped = center_crop(img2, w2, base_height)
        base_img.paste(img1_cropped, (0, 0))
        base_img.paste(img2_cropped, (w1, 0))
        draw_temp = ImageDraw.Draw(base_img)
        draw_temp.line([(w1, 0), (w1, base_height)], fill="#000000", width=4)
    elif img1:
        img1_cropped = center_crop(img1, base_width, base_height)
        base_img.paste(img1_cropped, (0, 0))
    else:
        # If no image was found, create a premium background with patriotic gradient color
        draw_temp = ImageDraw.Draw(base_img)
        draw_temp.rectangle([(0, 0), (base_width, base_height)], fill="#1B2A47") # Military dark blue
        
    overlay = Image.new('RGBA', (base_width, base_height), (0,0,0,0))
    draw_gradient(overlay, 600, 1050, color_start=(11,12,16,0), color_end=(11,12,16,255))
    base_img = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
    
    draw = ImageDraw.Draw(base_img)
    draw.rectangle([(0, 1050), (base_width, base_height)], fill="#0B0C10")
    
    if circle_image_url:
        badge_size = 300
        pos_y = int(700 - badge_size // 2)
        if len(headline) % 2 == 0:
            pos_x = 70
        else:
            pos_x = base_width - badge_size - 70
            
        pos_x = int(pos_x)
        pos_y = int(pos_y)
            
        draw_circular_badge(
            base_img, 
            flag_url_or_path=circle_image_url, 
            size=badge_size, 
            pos_x=pos_x, 
            pos_y=pos_y
        )
    
    if hook_text:
        combined_text = f"{headline} {hook_text}".upper()
    else:
        combined_text = headline.upper()
        
    combined_text = combined_text.replace("’", "'").replace("“", '"').replace("”", '"')
    combined_text = re.sub(r'[^\x00-\x7F*]+', '', combined_text)
    
    headline_length = len(combined_text)
    if headline_length < 40:
        font_size = 110
    elif headline_length < 70:
        font_size = 85
    elif headline_length < 100:
        font_size = 68
    else:
        font_size = 54
        
    text_font = get_font("anton", size=font_size)
    margin = 50
    max_text_width = base_width - (margin * 2)
    
    text_total_height = render_multicolor_text_centered(draw, combined_text, 0, text_font, max_text_width, base_width, dry_run=True)
    bottom_padding = 60
    text_start_y = base_height - bottom_padding - text_total_height
    
    # Blur only the text background area dynamically to keep the top of the image crystal clear
    blur_y_start = int(text_start_y - 140)
    if blur_y_start < 0:
        blur_y_start = 0
    bottom_crop = base_img.crop((0, blur_y_start, base_width, base_height))
    bottom_blurred = bottom_crop.filter(ImageFilter.GaussianBlur(15))
    base_img.paste(bottom_blurred, (0, blur_y_start))
    
    # Re-initialize draw context after pasting the blurred section
    draw = ImageDraw.Draw(base_img)
    
    # Try custom logo/banner first, otherwise print fallback text logo
    banner_path = "assets/logo/banner.png"
    if os.path.exists(banner_path):
        try:
            banner = Image.open(banner_path).convert("RGBA")
            bw, bh = banner.size
            new_bw = 500
            new_bh = int(bh * (new_bw / bw))
            banner = banner.resize((new_bw, new_bh), Image.Resampling.LANCZOS)
            bx = int((base_width - new_bw) // 2)
            by = int(text_start_y - new_bh - 25)
            base_img.paste(banner, (bx, by), banner)
        except Exception as e:
            logging.error(f"Failed to load user banner logo: {e}")
    else:
        # Fallback branding text
        try:
            brand_font = get_font("anton", size=36)
            brand_text = os.getenv("BRANDING_TEXT", "AMERICAN ARMY NEWS").upper()
            bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
            brand_w = bbox[2] - bbox[0]
            bx = (base_width - brand_w) // 2
            by = text_start_y - 65
            draw.text((bx, by), brand_text, font=brand_font, fill="#FFCC00")
        except Exception as e:
            logging.error(f"Failed to render fallback branding text: {e}")
            
    render_multicolor_text_centered(draw, combined_text, text_start_y, text_font, max_text_width, base_width)
    
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    base_img.save(output_path, quality=95)
    logging.info(f"Image saved to {output_path}")
    return output_path

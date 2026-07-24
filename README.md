# American Army News Agent

An automated, cloud-based Python agent that monitors Google News and Twitter (X) for the latest trends in the American Army & US Military, uses NVIDIA Nemotron LLM to generate highly engaging caption copy, designs custom posters using Pillow, uploads them automatically to your Facebook Page, and alerts you via a Discord Channel Webhook.

## Features
- **24/7 Automation**: Runs every 2 hours (12 posts per day) via GitHub Actions scheduler.
- **Smart Scraper**: Scrapes Google News RSS feeds for "American Army" / "US Military" news and contains stub integration for Twitter (X) search endpoints.
- **AI Content Generator**: Integrates with NVIDIA Nemotron LLM to generate headlines (MAX 10 words) with highlighted keywords, hooks, safety/policy checks, and captions.
- **Dynamic Poster Designer**: Custom Pillow engine that stitches background photos, overlays vertical gradients, adds a circular badge, centers typography, and outputs high-definition 1080x1350 images.
- **Facebook Publisher**: Auto-publishes to your Facebook Page via the Graph API.
- **Discord Alerts**: Instantly uploads the generated photo and details to your Discord channel.

## Installation & Setup
1. Create a Python Virtual Environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill out your secrets:
   ```env
   FACEBOOK_ACCESS_TOKEN="your_facebook_access_token"
   FACEBOOK_PAGE_ID="your_facebook_page_id"
   DISCORD_WEBHOOK_URL="your_discord_webhook"
   NVIDIA_API_KEY="your_nvidia_api_key"
   ```

## Local Dry-Run Testing
If `FACEBOOK_ACCESS_TOKEN` is not set or has the placeholder value, the program automatically operates in **Dry-Run Mode**. It fetches the news, generates the poster locally in the `output/` folder, print-logs the Facebook Caption, and saves the article title as processed in `output/processed_news.txt` to prevent repetition.

Run it locally:
```bash
python auto_agent.py
```

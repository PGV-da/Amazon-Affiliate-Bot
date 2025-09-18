#!/usr/bin/env python3
"""
Amazon-only Affiliate Forwarder
- Monitors multiple source channels
- Only processes Amazon product links
- Replaces any existing affiliate tag with AFFILIATE_TAG
- Shortens links using Bitly (if BITLY_TOKEN provided)
- Deduplicates using ASIN (persisted to posted_links.txt)
- Ignores messages that contain no Amazon links
- Lightweight rewriting kept optional
"""
import os
import re
import asyncio
import random
import logging
from typing import List, Optional, Set
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import FloodWaitError
import aiohttp
import dotenv

# ---------- CONFIG ----------
dotenv.load_dotenv()  # load .env file if present

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNELS_STR = os.getenv("SOURCE_CHANNELS")
TARGET_CHANNEL_STR = os.getenv("TARGET_CHANNEL")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
BITLY_TOKEN = os.getenv("BITLY_TOKEN")  # optional, to shorten links
REWRITE_LEVEL = float(os.getenv("REWRITE_LEVEL", "0.35"))  # small by default
EXTRA_HASHTAGS = os.getenv("EXTRA_HASHTAGS", "").strip()
PORT = int(os.getenv("PORT", "8080"))
ALERT_USER_ID_STR = os.getenv("ALERT_USER_ID")

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- VALIDATION ----------
if not all([API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS_STR, TARGET_CHANNEL_STR, AFFILIATE_TAG, ALERT_USER_ID_STR]):
    raise SystemExit("Missing required env vars: set API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS, TARGET_CHANNEL, AFFILIATE_TAG, ALERT_USER_ID")

try:
    API_ID = int(API_ID)
    ALERT_USER_ID = int(ALERT_USER_ID_STR)
except ValueError:
    raise SystemExit("API_ID and ALERT_USER_ID must be integers.")

source_channels: List[int | str] = []
for s in SOURCE_CHANNELS_STR.split(","):
    s = s.strip()
    if not s:
        continue
    if s.startswith("-100") or s.startswith("-"):
        source_channels.append(int(s))   # use integer for private channels/groups
    else:
        source_channels.append(s)

try:
    target_channel = int(TARGET_CHANNEL_STR)
except ValueError:
    target_channel = TARGET_CHANNEL_STR

# ---------- PERSISTENCE ----------
POSTED_DB = "posted_links.txt"
posted: Set[str] = set()
if os.path.exists(POSTED_DB):
    with open(POSTED_DB, "r", encoding="utf-8") as f:
        posted.update(line.strip() for line in f if line.strip())

# ---------- REGEX & REWRITES ----------
AMAZON_URL_RE = re.compile(r'https?://[^\s]*amazon\.[^\s/]+[^\s]*', re.I)
ASIN_PATTERNS = [
    re.compile(r'/dp/([A-Z0-9]{10})', re.I),
    re.compile(r'/gp/product/([A-Z0-9]{10})', re.I),
    re.compile(r'[?&]asin=([A-Z0-9]{10})', re.I),
]
SYNONYMS = {'buy': ['grab', 'get'], 'today': ['right now', 'today only']}

# ---------- HELPERS ----------
def extract_amazon_urls(text: str) -> List[str]:
    """Extracts all Amazon URLs from a given text."""
    return AMAZON_URL_RE.findall(text or "")

def get_asin(url: str) -> Optional[str]:
    """Extracts the ASIN from an Amazon URL."""
    for pat in ASIN_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1).upper()
    return None

def normalize_url_remove_tracking(url: str) -> str:
    """Removes affiliate tags and common tracking parameters from a URL."""
    url = re.sub(r'([?&])tag=[^&]*', '', url, flags=re.I)
    url = re.sub(r'([?&])utm_[^=]+=[^&]*', '', url, flags=re.I)
    url = re.sub(r'#.*$', '', url)
    return url.rstrip('?&')

def replace_amazon_tag(url: str) -> str:
    """Replaces or adds the affiliate tag to an Amazon URL."""
    url = normalize_url_remove_tracking(url)
    return f"{url}{'&' if '?' in url else '?'}{AFFILIATE_TAG}"

async def shorten_bitly(session: aiohttp.ClientSession, long_url: str) -> str:
    """Shortens a URL using Bitly, returns original on failure."""
    if not BITLY_TOKEN:
        return long_url
    api = "https://api-ssl.bitly.com/v4/shorten"
    headers = {"Authorization": f"Bearer {BITLY_TOKEN}", "Content-Type": "application/json"}
    payload = {"long_url": long_url}
    try:
        async with session.post(api, headers=headers, json=payload, timeout=10) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return data.get("link", long_url)
            else:
                text = await resp.text()
                logging.error(f"Bitly error: {resp.status} - {text}")
    except aiohttp.ClientError as e:
        logging.error(f"Bitly exception: {e}")
    return long_url

def persist_key(key: str):
    """Appends a key to the persistence file."""
    try:
        with open(POSTED_DB, "a", encoding="utf-8") as f:
            f.write(key + "\n")
    except IOError as e:
        logging.error(f"Persist error: {e}")

def light_rewrite(text: str) -> str:
    """Performs a light, optional rewrite of the text to avoid exact duplicates."""
    if not text or random.random() > REWRITE_LEVEL:
        return text
    tokens = re.split(r'(\W+)', text)
    out = []
    for t in tokens:
        low = t.lower()
        if low in SYNONYMS and random.random() < 0.5:
            repl = random.choice(SYNONYMS[low])
            out.append(repl.capitalize() if t.isupper() else repl)
        else:
            out.append(t)
    if EXTRA_HASHTAGS and random.random() < 0.3:
        out.append(" " + EXTRA_HASHTAGS)
    return "".join(out)

async def send_error_alert(client: TelegramClient, text: str):
    """Sends an error alert to the designated user."""
    try:
        await client.send_message(ALERT_USER_ID, f"🚨 **Bot Error Alert**\n{text}")
    except Exception as e:
        logging.error(f"Failed to send error alert: {e}")

# ---------- MAIN HANDLER ----------
async def process_message(event: events.NewMessage.Event, http_session: aiohttp.ClientSession):
    """Main handler for processing incoming messages."""
    text = event.message.message or ""
    amazon_urls = extract_amazon_urls(text)
    if not amazon_urls:
        return

    new_text = text
    posted_any = False
    for url in amazon_urls:
        asin = get_asin(url)
        key = asin or normalize_url_remove_tracking(url)
        if key in posted:
            continue

        aff_url = replace_amazon_tag(url)
        short_url = await shorten_bitly(http_session, aff_url)
        new_text = new_text.replace(url, short_url, 1)

        posted.add(key)
        persist_key(key)
        posted_any = True

    if not posted_any:
        return

    final_caption = light_rewrite(new_text)

    if event.message.media:
        await event.client.send_file(target_channel, event.message.media, caption=final_caption)
    else:
        await event.client.send_message(target_channel, final_caption)

# ---------- WEB SERVER & MAIN LOOP ----------
async def ping(request):
    return aiohttp.web.Response(text="pong")

async def main():
    """Main function to start the bot and web server."""
    async with aiohttp.ClientSession() as http_session, \
               TelegramClient("affiliate_bot", API_ID, API_HASH) as client:

        await client.start(bot_token=BOT_TOKEN)
        logging.info(f"Bot started. Monitoring channels: {source_channels}")

        @client.on(events.NewMessage(chats=source_channels))
        async def handler(event: events.NewMessage.Event):
            try:
                await process_message(event, http_session)
            except FloodWaitError as e:
                logging.warning(f"Flood wait: sleeping for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logging.exception("Handler error")
                await send_error_alert(client, str(e))

        # Start web server for uptime pings
        try:
            app = aiohttp.web.Application()
            app.router.add_get('/ping', ping)
            runner = aiohttp.web.AppRunner(app)
            await runner.setup()
            site = aiohttp.web.TCPSite(runner, '0.0.0.0', PORT)
            await site.start()
            logging.info(f"Web server started on port {PORT}")
        except Exception as e:
            logging.error(f"Webserver not started: {e}")
            await send_error_alert(client, f"Webserver failed to start: {e}")

        await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

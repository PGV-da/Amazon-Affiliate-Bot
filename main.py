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
import json
import asyncio
import random
import sys
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import aiohttp
import dotenv

dotenv.load_dotenv()

# ---------- CONFIG & VALIDATION ----------
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    SOURCE_CHANNELS_STR = os.getenv("SOURCE_CHANNELS")
    TARGET_CHANNEL_STR = os.getenv("TARGET_CHANNEL")
    AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
    ALERT_USER_ID_STR = os.getenv("ALERT_USER_ID")
except (ValueError, TypeError):
    sys.exit("ERROR: API_ID must be an integer. Please check your .env file.")

# Optional values
BITLY_TOKEN = os.getenv("BITLY_TOKEN", "")
REWRITE_LEVEL = float(os.getenv("REWRITE_LEVEL", "0.35"))
EXTRA_HASHTAGS = os.getenv("EXTRA_HASHTAGS", "").strip()
PORT = int(os.getenv("PORT", "8080"))

# --- Critical Validation ---
if not all([API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS_STR, TARGET_CHANNEL_STR, AFFILIATE_TAG, ALERT_USER_ID_STR]):
    sys.exit("ERROR: Missing required env vars. Ensure API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS, TARGET_CHANNEL, AFFILIATE_TAG, and ALERT_USER_ID are set.")

# --- Convert channel/user IDs to integers ---
# This is the key fix: Telegram bots MUST use numerical IDs.
try:
    source_channels = [int(s.strip()) for s in SOURCE_CHANNELS_STR.split(",") if s.strip()]
    TARGET_CHANNEL = int(TARGET_CHANNEL_STR)
    ALERT_USER_ID = int(ALERT_USER_ID_STR)
except ValueError:
    sys.exit("ERROR: SOURCE_CHANNELS, TARGET_CHANNEL, and ALERT_USER_ID must be numerical IDs (e.g., -100123456789 for channels, 12345678 for users). Do not use usernames like '@channel'.")


client = TelegramClient("affiliate_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ---------- Persistence ----------
POSTED_DB = "posted_links.txt"
posted = set()
if os.path.exists(POSTED_DB):
    with open(POSTED_DB, "r", encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l:
                posted.add(l)

# aiohttp session for bitly
http_session = aiohttp.ClientSession()

# ---------- Helpers ----------
AMAZON_URL_RE = re.compile(r'https?://[^\s]*amazon\.[^\s/]+[^\s]*', re.I)
ASIN_PATTERNS = [
    re.compile(r'/dp/([A-Z0-9]{10})', re.I),
    re.compile(r'/gp/product/([A-Z0-9]{10})', re.I),
    re.compile(r'[?&]asin=([A-Z0-9]{10})', re.I),
]

def extract_amazon_urls(text):
    return AMAZON_URL_RE.findall(text or "")

def get_asin(url):
    for pat in ASIN_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1).upper()
    return None

def normalize_url_remove_tracking(url):
    # remove tag= or &tag= and common utm params and fragments
    url = re.sub(r'([?&])tag=[^&]*', '', url, flags=re.I)
    url = re.sub(r'([?&])utm_[^=]+=[^&]*', '', url, flags=re.I)
    url = re.sub(r'#.*$', '', url)
    # remove leftover ? or & at end
    url = re.sub(r'[?&]$', '', url)
    return url

def replace_amazon_tag(url):
    url = normalize_url_remove_tracking(url)
    # append or replace tag param
    return f"{url}{'&' if '?' in url else '?'}tag={AFFILIATE_TAG}"

async def shorten_bitly(long_url):
    if not BITLY_TOKEN:
        return long_url
    api = "https://api-ssl.bitly.com/v4/shorten"
    headers = {"Authorization": f"Bearer {BITLY_TOKEN}", "Content-Type": "application/json"}
    payload = {"long_url": long_url}
    try:
        async with http_session.post(api, headers=headers, json=payload, timeout=10) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                return data.get("link", long_url)
            else:
                text = await resp.text()
                print(f"Bitly error: {resp.status} - {text}")
    except Exception as e:
        print(f"Bitly exception: {e}")
    return long_url

def persist_key(key):
    try:
        with open(POSTED_DB, "a", encoding="utf-8") as f:
            f.write(key + "\n")
    except Exception as e:
        print(f"Persist error: {e}")

SYN = {'buy':['grab','get'], 'today':['right now','today only']}
def light_rewrite(text):
    if not text or random.random() > REWRITE_LEVEL:
        return text
    tokens = re.split(r'(\W+)', text)
    out = []
    for t in tokens:
        low = t.lower()
        if low in SYN and random.random() < 0.5:
            repl = random.choice(SYN[low])
            out.append(repl.capitalize() if t and t[0].isupper() else repl)
        else:
            out.append(t)
    if EXTRA_HASHTAGS and random.random() < 0.3:
        out.append(" " + EXTRA_HASHTAGS)
    return "".join(out)

async def send_error_alert(text):
    try:
        await client.send_message(ALERT_USER_ID, f"🚨 **Bot Error Alert**\n{text}")
    except Exception as e:
        print(f"Failed to send error alert: {e}")

# ---------- Handlers ----------
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Handler for the /start command."""
    await event.respond('Hi! I am alive and running.')

@client.on(events.NewMessage(chats=source_channels))
async def handler(event):
    try:
        text = event.message.message or ""
        amazon_urls = extract_amazon_urls(text)
        if not amazon_urls:
            return

        posted_any = False
        new_text = text
        for url in amazon_urls:
            asin = get_asin(url)
            key = asin or normalize_url_remove_tracking(url)
            
            if key in posted:
                continue

            aff_url = replace_amazon_tag(url)
            short_url = await shorten_bitly(aff_url)
            new_text = new_text.replace(url, short_url, 1)

            posted.add(key)
            persist_key(key)
            posted_any = True

        if not posted_any:
            return

        final_caption = light_rewrite(new_text)

        if event.message.media:
            await client.send_file(TARGET_CHANNEL, event.message.media, caption=final_caption)
        else:
            await client.send_message(TARGET_CHANNEL, final_caption)

    except FloodWaitError as e:
        print(f"Flood wait: sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Handler error: {e}")
        await send_error_alert(f"Handler Error: {e}")

# ---------- Webserver for Uptime Pings ----------
async def start_web():
    try:
        from aiohttp import web
        async def ping(request):
            return web.Response(text="pong")
        
        app = web.Application()
        app.router.add_get('/ping', ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        print(f"Webserver started on port {PORT}.")
    except Exception as e:
        print(f"Could not start webserver: {e}")
        await send_error_alert(f"Webserver failed to start: {e}")

# ---------- Main Execution ----------
async def main():
    if 'aiohttp' in sys.modules:
        await start_web()
    print("Bot started. Monitoring channels:", source_channels)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        client.loop.run_until_complete(http_session.close())

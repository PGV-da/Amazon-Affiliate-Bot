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
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import aiohttp

# ---------- CONFIG ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SOURCE_CHANNELS = os.getenv("SOURCE_CHANNELS", "")  # comma separated (-100ids or usernames)
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "")    # -100id or @username
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "")
BITLY_TOKEN = os.getenv("BITLY_TOKEN", "")          # optional, to shorten links
REWRITE_LEVEL = float(os.getenv("REWRITE_LEVEL", "0.35"))  # small by default
EXTRA_HASHTAGS = os.getenv("EXTRA_HASHTAGS", "").strip()
PORT = int(os.getenv("PORT", "8080"))
ALERT_USER_ID = int(os.getenv("ALERT_USER_ID", "0"))  # Telegram user ID for error alerts

if not all([API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS, TARGET_CHANNEL, AFFILIATE_TAG, ALERT_USER_ID]):
    raise SystemExit("Missing required env vars: set API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNELS, TARGET_CHANNEL, AFFILIATE_TAG, ALERT_USER_ID")

source_channels = [s.strip() for s in SOURCE_CHANNELS.split(",") if s.strip()]

client = TelegramClient("affiliate_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# persistence
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

# ---------- helpers ----------
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
            if resp.status == 200 or resp.status == 201:
                data = await resp.json()
                return data.get("link", long_url)
            else:
                # fallback: don't shorten on error
                text = await resp.text()
                print("Bitly error:", resp.status, text)
    except Exception as e:
        print("Bitly exception:", e)
    return long_url

def persist_key(key):
    try:
        with open(POSTED_DB, "a", encoding="utf-8") as f:
            f.write(key + "\n")
    except Exception as e:
        print("Persist error:", e)

# small optional light rewriting to avoid exact duplicates (keeps meaning)
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
            out.append(repl.capitalize() if t[0].isupper() else repl)
        else:
            out.append(t)
    if EXTRA_HASHTAGS and random.random() < 0.3:
        out.append(" " + EXTRA_HASHTAGS)
    return "".join(out)

async def send_error_alert(text):
    try:
        await client.send_message(ALERT_USER_ID, f"🚨 **Bot Error Alert**\n{text}")
    except Exception as e:
        print("Failed to send error alert:", e)

# ---------- handler ----------
@client.on(events.NewMessage(chats=source_channels))
async def handler(event):
    try:
        text = event.message.message or ""
        # extract amazon urls only
        amazon_urls = extract_amazon_urls(text)
        if not amazon_urls:
            # ignore messages with no amazon links
            return

        # process each amazon url in message
        posted_any = False
        new_text = text
        for url in amazon_urls:
            asin = get_asin(url)
            if asin:
                key = asin
            else:
                # fallback: normalized url without query/fragments
                key = normalize_url_remove_tracking(url)
            if key in posted:
                # skip this URL (already posted)
                continue

            # replace tag to your affiliate
            aff = replace_amazon_tag(url)

            # shorten if bitly token set
            short = await shorten_bitly(aff)

            # replace original url in text with short affiliate url (first occurrence)
            new_text = new_text.replace(url, short, 1)

            # mark posted
            posted.add(key)
            persist_key(key)
            posted_any = True

        if not posted_any:
            # all links were duplicates -> do nothing
            return

        # rewrite lightly to avoid duplicates
        final_caption = light_rewrite(new_text)

        # send media if present else text
        if event.message.media:
            await client.send_file(TARGET_CHANNEL, event.message.media, caption=final_caption)
        else:
            await client.send_message(TARGET_CHANNEL, final_caption)

    except FloodWaitError as e:
        print("Flood wait:", e.seconds)
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print("Handler error:", e)
        await send_error_alert(str(e))

# ---------- tiny webserver for uptime pings ----------
try:
    from aiohttp import web
    async def ping(request):
        return web.Response(text="pong")
    async def start_web():
        app = web.Application()
        app.router.add_get('/ping', ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
except Exception as e:
    print("Webserver not started:", e)
    await send_error_alert(str(e))

print("Started. Monitoring:", source_channels)
client.run_until_disconnected()

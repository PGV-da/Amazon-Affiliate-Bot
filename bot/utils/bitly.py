import logging
import aiohttp
from bot.config import BITLY_TOKEN

# Initialize a single aiohttp session for the application
_session = aiohttp.ClientSession()

async def shorten_bitly(long_url: str) -> str:
    """
    Shortens a URL using the Bitly API.
    Returns the original URL if shortening fails or is disabled.
    """
    if not BITLY_TOKEN:
        return long_url

    api_url = "https://api-ssl.bitly.com/v4/shorten"
    headers = {"Authorization": f"Bearer {BITLY_TOKEN}", "Content-Type": "application/json"}
    payload = {"long_url": long_url}

    try:
        async with _session.post(api_url, headers=headers, json=payload, timeout=10) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                return data.get("link", long_url)
            else:
                text = await resp.text()
                logging.error(f"Bitly API error: {resp.status} - {text}")
    except Exception as e:
        logging.error(f"Bitly request exception: {e}")

    return long_url

async def close_session():
    """
    Gracefully closes the aiohttp session.
    """
    if not _session.closed:
        await _session.close()

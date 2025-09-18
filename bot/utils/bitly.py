import logging
import aiohttp
from bot.config import BITLY_TOKEN

_session = None

async def get_session() -> aiohttp.ClientSession:
    """
    Initializes and returns a single aiohttp.ClientSession instance.
    This ensures the session is created inside a running event loop.
    """
    global _session
    if _session is None or _session.closed:
        # Create the session inside an async function where the loop is running
        _session = aiohttp.ClientSession()
    return _session

async def shorten_bitly(long_url: str) -> str:
    """
    Shortens a URL using the Bitly API.
    Returns the original URL if shortening fails or is disabled.
    """
    if not BITLY_TOKEN:
        return long_url

    # ✅ CORRECT: Call our new async function to get the session.
    session = await get_session()
    
    api_url = "https://api-ssl.bitly.com/v4/shorten"
    headers = {"Authorization": f"Bearer {BITLY_TOKEN}", "Content-Type": "application/json"}
    payload = {"long_url": long_url}

    try:
        async with session.post(api_url, headers=headers, json=payload, timeout=10) as resp:
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
    global _session
    if _session and not _session.closed:
        await _session.close()


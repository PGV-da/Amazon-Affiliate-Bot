import random
import asyncio
import logging
# from turtle import delay
from telethon import events
from telethon.errors import FloodWaitError
from bot.config import SOURCE_CHANNELS, TARGET_CHANNEL
from bot.client import send_error_alert
from bot.utils import amazon, bitly, persistence, rewrite

@events.register(events.NewMessage(chats=SOURCE_CHANNELS))
async def user_client_message_handler(event):
    """
    Event handler for the user client to monitor non-admin channels.
    """
    try:
        text = event.message.message or ""
        amazon_urls = amazon.extract_amazon_urls(text)

        if not amazon_urls:
            return  # Ignore messages without Amazon links

        new_text = text
        posted_any = False

        for url in amazon_urls:
            asin = amazon.get_asin(url)
            key = asin or amazon.normalize_url_remove_tracking(url)

            if persistence.is_posted(key):
                continue  # Skip already posted links

            # Process the URL
            aff_url = amazon.replace_amazon_tag(url)
            short_url = await bitly.shorten_bitly(aff_url)
            new_text = new_text.replace(url, short_url, 1)

            # Mark as posted
            persistence.mark_as_posted(key)
            posted_any = True

        if not posted_any:
            return  # All links in the message were duplicates

        # Apply light text rewriting
        final_caption = rewrite.light_rewrite(new_text)

        # Wait for a random time between 2 and 5 seconds to act more human
        delay = random.uniform(2, 5)
        await asyncio.sleep(delay)

        # Forward the message
        if event.message.media:
            await event.client.send_file(TARGET_CHANNEL, event.message.media, caption=final_caption)
        else:
            await event.client.send_message(TARGET_CHANNEL, final_caption)
        
    except FloodWaitError as e:
        logging.warning(f"User client flood wait: sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logging.error(f"User client handler error: {e}", exc_info=True)
        await send_error_alert(f"An error occurred in the user client message handler: {e}")

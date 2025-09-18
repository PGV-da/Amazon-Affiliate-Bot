import logging
from telethon import TelegramClient
from bot.config import API_ID, API_HASH, BOT_TOKEN, ALERT_USER_ID

# Initialize the Telegram client
client = TelegramClient("affiliate_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def send_error_alert(text: str):
    """
    Sends an error alert to the designated user.
    """
    try:
        await client.send_message(ALERT_USER_ID, f"🚨 **Bot Error Alert**\n\n{text}")
    except Exception as e:
        logging.error(f"Failed to send error alert: {e}")

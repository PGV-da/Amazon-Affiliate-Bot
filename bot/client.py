import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from bot.config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, ALERT_USER_ID

# Initialize the Telegram client (existing bot)
client = TelegramClient("affiliate_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Initialize the user client for monitoring non-admin channels
user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def send_error_alert(text: str):
    """
    Sends an error alert to the designated user.
    """
    try:
        await client.send_message(ALERT_USER_ID, f"🚨 **Bot Error Alert**\n\n{text}")
    except Exception as e:
        logging.error(f"Failed to send error alert: {e}")

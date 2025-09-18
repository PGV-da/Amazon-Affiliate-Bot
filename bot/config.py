import os
import sys
from typing import List
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

def get_env_var(name: str, required: bool = True, default=None, cast_to=str):
    """
    Retrieves and casts an environment variable.
    Exits if a required variable is missing.
    """
    value = os.getenv(name)
    if required and not value:
        sys.exit(f"ERROR: Missing required environment variable: {name}")
    if value is None:
        return default
    try:
        return cast_to(value)
    except (ValueError, TypeError):
        sys.exit(f"ERROR: Could not cast environment variable {name} to {cast_to.__name__}.")

# --- Telegram API Credentials ---
API_ID: int = get_env_var("API_ID", cast_to=int)
API_HASH: str = get_env_var("API_HASH")
BOT_TOKEN: str = get_env_var("BOT_TOKEN")

# --- Channel/User IDs ---
SOURCE_CHANNELS_STR: str = get_env_var("SOURCE_CHANNELS")
TARGET_CHANNEL_STR: str = get_env_var("TARGET_CHANNEL")
ALERT_USER_ID_STR: str = get_env_var("ALERT_USER_ID")

try:
    SOURCE_CHANNELS: List[int] = [int(s.strip()) for s in SOURCE_CHANNELS_STR.split(",") if s.strip()]
    TARGET_CHANNEL: int = int(TARGET_CHANNEL_STR)
    ALERT_USER_ID: int = int(ALERT_USER_ID_STR)
except ValueError:
    sys.exit("ERROR: SOURCE_CHANNELS, TARGET_CHANNEL, and ALERT_USER_ID must be numerical IDs.")

# --- Affiliate and URL Shortener ---
AFFILIATE_TAG: str = get_env_var("AFFILIATE_TAG")
BITLY_TOKEN: str = get_env_var("BITLY_TOKEN", required=False, default="")

# --- Bot Behavior ---
REWRITE_LEVEL: float = get_env_var("REWRITE_LEVEL", required=False, default=0.35, cast_to=float)
EXTRA_HASHTAGS: str = get_env_var("EXTRA_HASHTAGS", required=False, default="").strip()

# --- Webserver ---
PORT: int = get_env_var("PORT", required=False, default=8080, cast_to=int)

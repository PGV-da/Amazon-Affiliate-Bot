# Amazon Affiliate Telegram Bot

This bot monitors specified Telegram channels for Amazon product links, replaces the affiliate tag with your own, shortens the links using Bitly (optional), and forwards the messages to a target channel.

It's designed to be efficient and robust, handling deduplication of links to avoid spamming and providing error alerts.

## Project Structure

The project is organized into a clean, multi-file structure to separate concerns and improve maintainability.

```
.
├── .env.example
├── README.md
├── requirements.txt
├── main.py
└── bot/
    ├── __init__.py
    ├── client.py
    ├── config.py
    ├── webserver.py
    ├── handlers/
    │   ├── __init__.py
    │   ├── command_handler.py
    │   └── message_handler.py
    └── utils/
        ├── __init__.py
        ├── amazon.py
        ├── bitly.py
        ├── persistence.py
        └── rewrite.py
```

- **`main.py`**: The main entry point of the application.
- **`bot/config.py`**: Manages all configuration from environment variables.
- **`bot/client.py`**: Initializes the Telegram client.
- **`bot/webserver.py`**: Runs a simple webserver for uptime monitoring.
- **`bot/handlers/`**: Contains the logic for handling different types of Telegram events (commands, messages).
- **`bot/utils/`**: A package of helper modules for specific tasks like URL processing, data persistence, and text rewriting.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install Dependencies

Create a virtual environment and install the required packages.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example `.env` file and fill in your details.

```bash
cp .env.example .env
```

Now, edit the `.env` file with your favorite editor and provide your credentials.

**Important:**
- `API_ID`, `API_HASH`, and `BOT_TOKEN` are obtained from Telegram.
- `SOURCE_CHANNELS`, `TARGET_CHANNEL`, and `ALERT_USER_ID` **must be numerical IDs**. You can get these from a bot like `@userinfobot`. Do not use usernames like `@mychannel`.

### 4. Run the Bot

Once configured, you can start the bot:

```bash
python main.py
```

The bot will log in and start monitoring the source channels.

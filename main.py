import asyncio
import logging
from bot.client import client, user_client, send_error_alert
from bot.handlers import command_handler, message_handler
from bot.webserver import start_web
from bot.utils.bitly import close_session as close_bitly_session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Main function to initialize and run the bot.
    """
    # Register event handlers for the bot client
    client.add_event_handler(command_handler.start)
    
    # Register event handler for the user client
    user_client.add_event_handler(message_handler.user_client_message_handler)

    # Start the webserver for uptime pings
    await start_web()

    logging.info("Bot started and ready.")
    
    # Connect the user client and run both clients concurrently
    await user_client.start()
    await asyncio.gather(
        client.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except Exception as e:
        logging.critical(f"Critical error: {e}")
        # Send an alert on critical failure if possible
        try:
            client.loop.run_until_complete(send_error_alert(f"Bot shut down due to critical error: {e}"))
        except Exception as alert_e:
            logging.error(f"Failed to send critical error alert: {alert_e}")
    finally:
        # Gracefully close sessions
        client.loop.run_until_complete(close_bitly_session())
        logging.info("Bot stopped.")

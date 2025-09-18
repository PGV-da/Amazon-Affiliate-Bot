import logging
from aiohttp import web
from bot.config import PORT
from bot.client import send_error_alert

async def ping(request):
    """A simple handler that returns 'pong'."""
    return web.Response(text="pong")

async def start_web():
    """
    Initializes and starts the aiohttp webserver.
    """
    try:
        app = web.Application()
        app.router.add_get('/ping', ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logging.info(f"Webserver started successfully on port {PORT}.")
    except Exception as e:
        logging.error(f"Could not start webserver: {e}")
        await send_error_alert(f"Webserver failed to start: {e}")

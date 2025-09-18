from telethon import events

@events.register(events.NewMessage(pattern='/start'))
async def start(event):
    """
    Handler for the /start command.
    Responds with a simple "alive" message.
    """
    await event.respond('Hi! I am the Amazon Affiliate Bot, and I am alive and running.')

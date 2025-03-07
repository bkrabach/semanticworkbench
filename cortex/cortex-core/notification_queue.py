# notification_queue.py

import asyncio

# Global notification queue to hold output notifications.
notification_queue = asyncio.Queue()

async def push_notification(message: str):
    """
    Push a notification message to the global queue.
    
    Args:
        message (str): The notification text.
    """
    await notification_queue.put(message)

async def get_notification() -> str:
    """
    Retrieve a notification message from the global queue.
    
    Returns:
        str: The notification message.
    """
    return await notification_queue.get()

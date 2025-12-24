from typing import List, Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from app.database.models import Channel


async def check_subscription(bot: Bot, user_id: int, channels: List[Channel]) -> List[Channel]:
    """
    Check user subscription to channels.
    Returns list of channels user is NOT subscribed to.
    """
    not_subscribed = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.channel_id, user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                not_subscribed.append(channel)
        except TelegramBadRequest:
            # Bot might not be admin or channel doesn't exist
            pass

    return not_subscribed


async def check_bot_admin(bot: Bot, channel_id: int) -> bool:
    """Check if bot is admin in the channel."""
    try:
        member = await bot.get_chat_member(channel_id, bot.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except TelegramBadRequest:
        return False


async def get_channel_info(bot: Bot, channel_identifier: str) -> Optional[dict]:
    """
    Get channel information by ID or username.
    Returns dict with channel_id, title, username.
    """
    try:
        # Try to parse as integer ID
        try:
            channel_id = int(channel_identifier)
        except ValueError:
            # It's a username
            channel_id = channel_identifier

        chat = await bot.get_chat(channel_id)

        return {
            "channel_id": chat.id,
            "title": chat.title or chat.full_name,
            "username": chat.username
        }
    except TelegramBadRequest:
        return None


def format_number(n: int) -> str:
    """Format number with thousand separators."""
    return f"{n:,}".replace(",", " ")


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def generate_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Generate a text progress bar."""
    if total == 0:
        percentage = 0
    else:
        percentage = current / total

    filled = int(length * percentage)
    empty = length - filled

    bar = "█" * filled + "░" * empty
    return f"{bar} {percentage*100:.1f}%"

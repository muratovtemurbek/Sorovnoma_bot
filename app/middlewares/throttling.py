from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import redis.asyncio as redis
from datetime import datetime

from app.config import (
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    MAX_MESSAGES_PER_MINUTE, BLOCK_DURATION_MINUTES
)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await redis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        )

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not self.redis:
            await self.connect()

        user_id = event.from_user.id
        key = f"throttle:{user_id}"

        try:
            # Get current count
            count = await self.redis.get(key)
            count = int(count) if count else 0

            if count >= MAX_MESSAGES_PER_MINUTE:
                # User is rate limited
                if isinstance(event, Message):
                    await event.answer("Juda ko'p so'rov! Biroz kuting.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Juda ko'p so'rov!", show_alert=True)
                return

            # Increment counter
            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 60)  # 1 minute expiry
            await pipe.execute()

        except Exception:
            # If Redis fails, let the request through
            pass

        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = await redis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        )

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not self.redis:
            await self.connect()

        user_id = event.from_user.id
        block_key = f"blocked:{user_id}"

        try:
            # Check if user is blocked
            blocked = await self.redis.get(block_key)
            if blocked:
                if isinstance(event, Message):
                    await event.answer("Siz vaqtincha bloklangansiz!")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Siz bloklangansiz!", show_alert=True)
                return

        except Exception:
            pass

        return await handler(event, data)

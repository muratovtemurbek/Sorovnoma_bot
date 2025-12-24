import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from app.config import BOT_TOKEN
from app.database.database_sqlite import db
from app.handlers import user, admin
# from app.middlewares.throttling import ThrottlingMiddleware, AntiSpamMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Actions on bot startup."""
    logger.info("Bot starting...")

    # Connect to database
    await db.connect()
    logger.info("Database connected")

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot):
    """Actions on bot shutdown."""
    logger.info("Bot shutting down...")

    # Close database connection
    await db.close()
    logger.info("Database connection closed")


async def scheduled_tasks(bot: Bot):
    """Background tasks for scheduled polls and posts."""
    while True:
        try:
            # Check for scheduled polls
            scheduled_polls = await db.get_scheduled_polls()
            for poll in scheduled_polls:
                try:
                    from app.keyboards.keyboards import poll_options_keyboard
                    options = await db.get_poll_options(poll.id)
                    keyboard = poll_options_keyboard(poll.id, options, poll.button_layout, False)

                    if poll.media_type == "photo" and poll.media_id:
                        msg = await bot.send_photo(
                            poll.channel_id,
                            poll.media_id,
                            caption=poll.text,
                            reply_markup=keyboard
                        )
                    elif poll.media_type == "video" and poll.media_id:
                        msg = await bot.send_video(
                            poll.channel_id,
                            poll.media_id,
                            caption=poll.text,
                            reply_markup=keyboard
                        )
                    else:
                        msg = await bot.send_message(
                            poll.channel_id,
                            poll.text,
                            reply_markup=keyboard
                        )

                    await db.update_poll(poll.id, message_id=msg.message_id, status="active")
                    logger.info(f"Published scheduled poll {poll.id}")
                except Exception as e:
                    logger.error(f"Failed to publish poll {poll.id}: {e}")

            # Check for polls that should end
            from datetime import datetime, timedelta
            expired_polls = await db.get_expired_polls()
            for poll in expired_polls:
                await db.update_poll(poll.id, status="finished")
                logger.info(f"Finished expired poll {poll.id}")

            # Check for scheduled posts
            import json
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            pending_posts = await db.get_pending_scheduled_posts()
            for post in pending_posts:
                try:
                    # Build keyboard from buttons
                    keyboard = None
                    if post.buttons:
                        buttons_data = json.loads(post.buttons)
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text=btn["text"], url=btn["url"])]
                            for btn in buttons_data
                        ])

                    # Send to all channels
                    for channel_id in post.channels:
                        try:
                            if post.media_type == "photo" and post.media_id:
                                await bot.send_photo(channel_id, post.media_id, caption=post.text, reply_markup=keyboard)
                            elif post.media_type == "video" and post.media_id:
                                await bot.send_video(channel_id, post.media_id, caption=post.text, reply_markup=keyboard)
                            elif post.media_type == "document" and post.media_id:
                                await bot.send_document(channel_id, post.media_id, caption=post.text, reply_markup=keyboard)
                            else:
                                await bot.send_message(channel_id, post.text, reply_markup=keyboard)
                        except Exception as e:
                            logger.error(f"Failed to send post {post.id} to channel {channel_id}: {e}")

                    # Handle repeat type
                    if post.repeat_type == "once":
                        await db.update_scheduled_post(post.id, status="sent")
                    elif post.repeat_type == "daily":
                        next_time = post.scheduled_at + timedelta(days=1)
                        await db.update_scheduled_post(post.id, scheduled_at=next_time)
                    elif post.repeat_type == "weekly":
                        next_time = post.scheduled_at + timedelta(weeks=1)
                        await db.update_scheduled_post(post.id, scheduled_at=next_time)

                    logger.info(f"Sent scheduled post {post.id}")
                except Exception as e:
                    logger.error(f"Failed to send post {post.id}: {e}")

        except Exception as e:
            logger.error(f"Scheduled task error: {e}")

        await asyncio.sleep(60)  # Check every minute


async def main():
    """Main function."""
    # Initialize bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares (disabled - requires Redis)
    # throttling = ThrottlingMiddleware()
    # antispam = AntiSpamMiddleware()
    # dp.message.middleware(throttling)
    # dp.callback_query.middleware(throttling)
    # dp.message.middleware(antispam)
    # dp.callback_query.middleware(antispam)

    # Register routers
    dp.include_router(user.router)
    dp.include_router(admin.router)

    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start background tasks
    asyncio.create_task(scheduled_tasks(bot))

    # Start polling
    logger.info("Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")

import asyncpg
from typing import Optional, List, Any
from datetime import datetime, timedelta
import json

from app.config import DATABASE_URL
from app.database.models import User, Admin, Channel, Poll, PollOption, Vote, CaptchaAttempt, ScheduledPost


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        await self.create_tables()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    full_name VARCHAR(255) NOT NULL,
                    phone VARCHAR(20),
                    language VARCHAR(5) DEFAULT 'uz',
                    is_blocked BOOLEAN DEFAULT FALSE,
                    spam_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    full_name VARCHAR(255) NOT NULL,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    permissions TEXT DEFAULT '[]',
                    added_by BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    title VARCHAR(255) NOT NULL,
                    is_mandatory BOOLEAN DEFAULT FALSE,
                    is_poll_channel BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    added_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    message_id BIGINT,
                    name VARCHAR(255) NOT NULL,
                    text TEXT NOT NULL,
                    media_type VARCHAR(20),
                    media_id VARCHAR(255),
                    button_layout INTEGER DEFAULT 1,
                    results_visibility VARCHAR(20) DEFAULT 'realtime',
                    status VARCHAR(20) DEFAULT 'draft',
                    scheduled_at TIMESTAMP,
                    ends_at TIMESTAMP,
                    end_votes_count INTEGER,
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS poll_options (
                    id SERIAL PRIMARY KEY,
                    poll_id INTEGER REFERENCES polls(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    photo_id VARCHAR(255),
                    position INTEGER DEFAULT 0,
                    votes_count INTEGER DEFAULT 0
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS votes (
                    id SERIAL PRIMARY KEY,
                    poll_id INTEGER REFERENCES polls(id) ON DELETE CASCADE,
                    option_id INTEGER REFERENCES poll_options(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    voted_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(poll_id, user_id)
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id SERIAL PRIMARY KEY,
                    channels TEXT NOT NULL,
                    text TEXT NOT NULL,
                    media_type VARCHAR(20),
                    media_id VARCHAR(255),
                    buttons TEXT,
                    scheduled_at TIMESTAMP NOT NULL,
                    repeat_type VARCHAR(20) DEFAULT 'once',
                    status VARCHAR(20) DEFAULT 'pending',
                    created_by BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS captcha_attempts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    correct_answer VARCHAR(20) NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    is_passed BOOLEAN DEFAULT FALSE,
                    blocked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

    # ============ USER METHODS ============
    async def get_user(self, telegram_id: int) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )
            if row:
                return User(**dict(row))
            return None

    async def create_user(self, telegram_id: int, full_name: str, username: str = None,
                          phone: str = None, language: str = "uz") -> User:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO users (telegram_id, username, full_name, phone, language)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
            ''', telegram_id, username, full_name, phone, language)
            return User(**dict(row))

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[User]:
        if not kwargs:
            return await self.get_user(telegram_id)

        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
        values = [telegram_id] + list(kwargs.values())

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f'''
                UPDATE users SET {set_clause}, updated_at = NOW()
                WHERE telegram_id = $1
                RETURNING *
            ''', *values)
            if row:
                return User(**dict(row))
            return None

    async def get_users_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM users")

    async def get_users_count_today(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE"
            )

    async def get_users_count_week(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days'"
            )

    async def get_users_count_month(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days'"
            )

    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit, offset
            )
            return [User(**dict(row)) for row in rows]

    async def search_users(self, query: str) -> List[User]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM users
                WHERE full_name ILIKE $1
                   OR phone ILIKE $1
                   OR CAST(telegram_id AS TEXT) LIKE $1
                ORDER BY created_at DESC LIMIT 50
            ''', f"%{query}%")
            return [User(**dict(row)) for row in rows]

    async def get_blocked_users(self) -> List[User]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE is_blocked = TRUE ORDER BY updated_at DESC"
            )
            return [User(**dict(row)) for row in rows]

    async def check_phone_exists(self, phone: str, exclude_telegram_id: int = None) -> bool:
        async with self.pool.acquire() as conn:
            if exclude_telegram_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE phone = $1 AND telegram_id != $2",
                    phone, exclude_telegram_id
                )
            else:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE phone = $1", phone
                )
            return result > 0

    # ============ ADMIN METHODS ============
    async def get_admin(self, telegram_id: int) -> Optional[Admin]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM admins WHERE telegram_id = $1", telegram_id
            )
            if row:
                data = dict(row)
                data['permissions'] = json.loads(data['permissions'])
                return Admin(**data)
            return None

    async def create_admin(self, telegram_id: int, full_name: str, username: str = None,
                           is_super_admin: bool = False, permissions: List[str] = None,
                           added_by: int = None) -> Admin:
        async with self.pool.acquire() as conn:
            perms = json.dumps(permissions or [])
            row = await conn.fetchrow('''
                INSERT INTO admins (telegram_id, username, full_name, is_super_admin, permissions, added_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            ''', telegram_id, username, full_name, is_super_admin, perms, added_by)
            data = dict(row)
            data['permissions'] = json.loads(data['permissions'])
            return Admin(**data)

    async def update_admin_permissions(self, telegram_id: int, permissions: List[str]) -> Optional[Admin]:
        async with self.pool.acquire() as conn:
            perms = json.dumps(permissions)
            row = await conn.fetchrow('''
                UPDATE admins SET permissions = $2
                WHERE telegram_id = $1
                RETURNING *
            ''', telegram_id, perms)
            if row:
                data = dict(row)
                data['permissions'] = json.loads(data['permissions'])
                return Admin(**data)
            return None

    async def delete_admin(self, telegram_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM admins WHERE telegram_id = $1 AND is_super_admin = FALSE",
                telegram_id
            )
            return result == "DELETE 1"

    async def get_all_admins(self) -> List[Admin]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM admins ORDER BY created_at DESC")
            admins = []
            for row in rows:
                data = dict(row)
                data['permissions'] = json.loads(data['permissions'])
                admins.append(Admin(**data))
            return admins

    # ============ CHANNEL METHODS ============
    async def get_channel(self, channel_id: int) -> Optional[Channel]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM channels WHERE channel_id = $1", channel_id
            )
            if row:
                return Channel(**dict(row))
            return None

    async def create_channel(self, channel_id: int, title: str, username: str = None,
                             is_mandatory: bool = False, is_poll_channel: bool = True,
                             added_by: int = 0) -> Channel:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO channels (channel_id, username, title, is_mandatory, is_poll_channel, added_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            ''', channel_id, username, title, is_mandatory, is_poll_channel, added_by)
            return Channel(**dict(row))

    async def update_channel(self, channel_id: int, **kwargs) -> Optional[Channel]:
        if not kwargs:
            return await self.get_channel(channel_id)

        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
        values = [channel_id] + list(kwargs.values())

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f'''
                UPDATE channels SET {set_clause}
                WHERE channel_id = $1
                RETURNING *
            ''', *values)
            if row:
                return Channel(**dict(row))
            return None

    async def delete_channel(self, channel_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM channels WHERE channel_id = $1", channel_id
            )
            return result == "DELETE 1"

    async def get_all_channels(self) -> List[Channel]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM channels WHERE is_active = TRUE ORDER BY created_at DESC"
            )
            return [Channel(**dict(row)) for row in rows]

    async def get_mandatory_channels(self) -> List[Channel]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM channels WHERE is_mandatory = TRUE AND is_active = TRUE"
            )
            return [Channel(**dict(row)) for row in rows]

    async def get_poll_channels(self) -> List[Channel]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM channels WHERE is_poll_channel = TRUE AND is_active = TRUE"
            )
            return [Channel(**dict(row)) for row in rows]

    # ============ POLL METHODS ============
    async def create_poll(self, channel_id: int, name: str, text: str, created_by: int,
                          media_type: str = None, media_id: str = None,
                          button_layout: int = 1, results_visibility: str = "realtime",
                          scheduled_at: datetime = None, ends_at: datetime = None,
                          end_votes_count: int = None) -> Poll:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO polls (channel_id, name, text, media_type, media_id,
                    button_layout, results_visibility, scheduled_at, ends_at,
                    end_votes_count, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
            ''', channel_id, name, text, media_type, media_id, button_layout,
                results_visibility, scheduled_at, ends_at, end_votes_count, created_by)
            return Poll(**dict(row))

    async def get_poll(self, poll_id: int) -> Optional[Poll]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM polls WHERE id = $1", poll_id)
            if row:
                return Poll(**dict(row))
            return None

    async def update_poll(self, poll_id: int, **kwargs) -> Optional[Poll]:
        if not kwargs:
            return await self.get_poll(poll_id)

        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
        values = [poll_id] + list(kwargs.values())

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f'''
                UPDATE polls SET {set_clause}
                WHERE id = $1
                RETURNING *
            ''', *values)
            if row:
                return Poll(**dict(row))
            return None

    async def get_active_polls(self) -> List[Poll]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM polls WHERE status = 'active' ORDER BY created_at DESC"
            )
            return [Poll(**dict(row)) for row in rows]

    async def get_polls_by_status(self, status: str) -> List[Poll]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM polls WHERE status = $1 ORDER BY created_at DESC", status
            )
            return [Poll(**dict(row)) for row in rows]

    async def get_scheduled_polls(self) -> List[Poll]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM polls
                WHERE status = 'scheduled' AND scheduled_at <= NOW()
                ORDER BY scheduled_at ASC
            ''')
            return [Poll(**dict(row)) for row in rows]

    async def get_polls_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM polls")

    async def get_active_polls_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM polls WHERE status = 'active'")

    # ============ POLL OPTIONS METHODS ============
    async def create_poll_option(self, poll_id: int, name: str, position: int,
                                  photo_id: str = None) -> PollOption:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO poll_options (poll_id, name, photo_id, position)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            ''', poll_id, name, photo_id, position)
            return PollOption(**dict(row))

    async def get_poll_options(self, poll_id: int) -> List[PollOption]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM poll_options WHERE poll_id = $1 ORDER BY position",
                poll_id
            )
            return [PollOption(**dict(row)) for row in rows]

    async def increment_option_votes(self, option_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE poll_options SET votes_count = votes_count + 1 WHERE id = $1",
                option_id
            )

    # ============ VOTE METHODS ============
    async def create_vote(self, poll_id: int, option_id: int, user_id: int) -> Optional[Vote]:
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow('''
                    INSERT INTO votes (poll_id, option_id, user_id)
                    VALUES ($1, $2, $3)
                    RETURNING *
                ''', poll_id, option_id, user_id)
                await self.increment_option_votes(option_id)
                return Vote(**dict(row))
            except asyncpg.UniqueViolationError:
                return None

    async def get_user_vote(self, poll_id: int, user_id: int) -> Optional[Vote]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM votes WHERE poll_id = $1 AND user_id = $2",
                poll_id, user_id
            )
            if row:
                return Vote(**dict(row))
            return None

    async def get_poll_votes(self, poll_id: int) -> List[Vote]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM votes WHERE poll_id = $1 ORDER BY voted_at", poll_id
            )
            return [Vote(**dict(row)) for row in rows]

    async def get_total_votes_count(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM votes")

    async def get_votes_count_today(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM votes WHERE voted_at::date = CURRENT_DATE"
            )

    async def get_poll_voters_with_details(self, poll_id: int) -> List[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT u.full_name, u.phone, po.name as option_name, v.voted_at
                FROM votes v
                JOIN users u ON v.user_id = u.id
                JOIN poll_options po ON v.option_id = po.id
                WHERE v.poll_id = $1
                ORDER BY v.voted_at
            ''', poll_id)
            return [dict(row) for row in rows]

    # ============ CAPTCHA METHODS ============
    async def create_captcha(self, user_id: int, correct_answer: str) -> CaptchaAttempt:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM captcha_attempts WHERE user_id = $1", user_id
            )
            row = await conn.fetchrow('''
                INSERT INTO captcha_attempts (user_id, correct_answer)
                VALUES ($1, $2)
                RETURNING *
            ''', user_id, correct_answer)
            return CaptchaAttempt(**dict(row))

    async def get_captcha(self, user_id: int) -> Optional[CaptchaAttempt]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM captcha_attempts WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if row:
                return CaptchaAttempt(**dict(row))
            return None

    async def update_captcha_attempts(self, user_id: int, attempts: int,
                                       is_passed: bool = False,
                                       blocked_until: datetime = None) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE captcha_attempts
                SET attempts = $2, is_passed = $3, blocked_until = $4
                WHERE user_id = $1
            ''', user_id, attempts, is_passed, blocked_until)

    # ============ SCHEDULED POSTS METHODS ============
    async def create_scheduled_post(self, channels: List[int], text: str, created_by: int,
                                     media_type: str = None, media_id: str = None,
                                     buttons: str = None, scheduled_at: datetime = None,
                                     repeat_type: str = "once") -> ScheduledPost:
        async with self.pool.acquire() as conn:
            channels_json = json.dumps(channels)
            row = await conn.fetchrow('''
                INSERT INTO scheduled_posts (channels, text, media_type, media_id,
                    buttons, scheduled_at, repeat_type, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            ''', channels_json, text, media_type, media_id, buttons,
                scheduled_at, repeat_type, created_by)
            data = dict(row)
            data['channels'] = json.loads(data['channels'])
            return ScheduledPost(**data)

    async def get_scheduled_post(self, post_id: int) -> Optional[ScheduledPost]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM scheduled_posts WHERE id = $1", post_id
            )
            if row:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                return ScheduledPost(**data)
            return None

    async def update_scheduled_post(self, post_id: int, **kwargs) -> Optional[ScheduledPost]:
        if not kwargs:
            return await self.get_scheduled_post(post_id)

        if 'channels' in kwargs:
            kwargs['channels'] = json.dumps(kwargs['channels'])

        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
        values = [post_id] + list(kwargs.values())

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f'''
                UPDATE scheduled_posts SET {set_clause}
                WHERE id = $1
                RETURNING *
            ''', *values)
            if row:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                return ScheduledPost(**data)
            return None

    async def delete_scheduled_post(self, post_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM scheduled_posts WHERE id = $1", post_id
            )
            return result == "DELETE 1"

    async def get_pending_scheduled_posts(self) -> List[ScheduledPost]:
        """Get posts that are due to be sent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM scheduled_posts
                WHERE status = 'pending' AND scheduled_at <= NOW()
                ORDER BY scheduled_at ASC
            ''')
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                posts.append(ScheduledPost(**data))
            return posts

    async def get_scheduled_posts_by_status(self, status: str) -> List[ScheduledPost]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM scheduled_posts WHERE status = $1 ORDER BY scheduled_at DESC",
                status
            )
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                posts.append(ScheduledPost(**data))
            return posts

    async def get_all_scheduled_posts(self, limit: int = 50) -> List[ScheduledPost]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM scheduled_posts ORDER BY created_at DESC LIMIT $1",
                limit
            )
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                posts.append(ScheduledPost(**data))
            return posts


db = Database()

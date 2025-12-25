import aiosqlite
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os

from app.database.models import User, Admin, Channel, Poll, PollOption, Vote, CaptchaAttempt, ScheduledPost

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bot.db")


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._conn = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.db_path, timeout=30.0)
        self._conn.row_factory = aiosqlite.Row
        # Ma'lumotlar xavfsizligi uchun FULL synchronous mode
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=FULL")
        await self._conn.execute("PRAGMA cache_size=10000")
        await self._conn.execute("PRAGMA wal_autocheckpoint=100")
        await self._conn.execute("PRAGMA busy_timeout=30000")
        await self.create_tables()
        await self._create_indexes()
        await self._conn.commit()

    async def close(self):
        if self._conn:
            try:
                # WAL faylini asosiy bazaga yozish
                await self._conn.execute("PRAGMA wal_checkpoint(FULL)")
                await self._conn.commit()
            except Exception:
                pass  # Ignore errors during checkpoint
            finally:
                try:
                    await self._conn.close()
                except Exception:
                    pass
                self._conn = None

    async def _get_connection(self):
        if self._conn is None:
            await self.connect()
        return self._conn

    async def _create_indexes(self):
        conn = await self._get_connection()
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_channels_channel_id ON channels(channel_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_status ON polls(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll_user ON votes(poll_id, user_id)")
        await conn.commit()

    async def create_tables(self):
        conn = self._conn
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT,
                language TEXT DEFAULT 'uz',
                is_blocked INTEGER DEFAULT 0,
                spam_score INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                is_super_admin INTEGER DEFAULT 0,
                permissions TEXT DEFAULT '[]',
                added_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                title TEXT NOT NULL,
                channel_type TEXT DEFAULT 'telegram_channel',
                is_mandatory INTEGER DEFAULT 0,
                is_poll_channel INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                added_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add channel_type column if not exists (migration)
        try:
            await conn.execute("ALTER TABLE channels ADD COLUMN channel_type TEXT DEFAULT 'telegram_channel'")
            await conn.commit()
        except:
            pass
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                name TEXT NOT NULL,
                text TEXT NOT NULL,
                media_type TEXT,
                media_id TEXT,
                button_layout INTEGER DEFAULT 1,
                results_visibility TEXT DEFAULT 'realtime',
                status TEXT DEFAULT 'draft',
                scheduled_at TEXT,
                ends_at TEXT,
                end_votes_count INTEGER,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS poll_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER,
                name TEXT NOT NULL,
                photo_id TEXT,
                position INTEGER DEFAULT 0,
                votes_count INTEGER DEFAULT 0,
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER,
                option_id INTEGER,
                user_id INTEGER,
                voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(poll_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channels TEXT NOT NULL,
                text TEXT NOT NULL,
                media_type TEXT,
                media_id TEXT,
                buttons TEXT,
                scheduled_at TEXT NOT NULL,
                repeat_type TEXT DEFAULT 'once',
                status TEXT DEFAULT 'pending',
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS captcha_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                correct_answer TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                is_passed INTEGER DEFAULT 0,
                blocked_until TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.commit()

    # ============ USER METHODS ============
    async def get_user(self, telegram_id: int) -> Optional[User]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['is_blocked'] = bool(data['is_blocked'])
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                data['updated_at'] = datetime.fromisoformat(data['updated_at']) if data['updated_at'] else datetime.now()
                return User(**data)
            return None

    async def create_user(self, telegram_id: int, full_name: str, username: str = None,
                          phone: str = None, language: str = "uz") -> User:
        conn = await self._get_connection()
        await conn.execute('''
            INSERT INTO users (telegram_id, username, full_name, phone, language)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, username, full_name, phone, language))
        await conn.commit()
        return await self.get_user(telegram_id)

    async def update_user(self, telegram_id: int, **kwargs) -> Optional[User]:
        if not kwargs:
            return await self.get_user(telegram_id)
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]
        conn = await self._get_connection()
        await conn.execute(f'''
            UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', values)
        await conn.commit()
        return await self.get_user(telegram_id)

    async def get_users_count(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_users_count_today(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_users_count_week(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_users_count_month(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-30 days')") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)) as cursor:
            rows = await cursor.fetchall()
            users = []
            for row in rows:
                data = dict(row)
                data['is_blocked'] = bool(data['is_blocked'])
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                data['updated_at'] = datetime.fromisoformat(data['updated_at']) if data['updated_at'] else datetime.now()
                users.append(User(**data))
            return users

    async def check_phone_exists(self, phone: str, exclude_telegram_id: int = None) -> bool:
        conn = await self._get_connection()
        if exclude_telegram_id:
            async with conn.execute("SELECT COUNT(*) FROM users WHERE phone = ? AND telegram_id != ?", (phone, exclude_telegram_id)) as cursor:
                row = await cursor.fetchone()
        else:
            async with conn.execute("SELECT COUNT(*) FROM users WHERE phone = ?", (phone,)) as cursor:
                row = await cursor.fetchone()
        return row[0] > 0 if row else False

    # ============ ADMIN METHODS ============
    async def get_admin(self, telegram_id: int) -> Optional[Admin]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM admins WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['is_super_admin'] = bool(data['is_super_admin'])
                data['permissions'] = json.loads(data['permissions'])
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                return Admin(**data)
            return None

    async def create_admin(self, telegram_id: int, full_name: str, username: str = None,
                           is_super_admin: bool = False, permissions: List[str] = None,
                           added_by: int = None) -> Admin:
        conn = await self._get_connection()
        perms = json.dumps(permissions or [])
        await conn.execute('''
            INSERT INTO admins (telegram_id, username, full_name, is_super_admin, permissions, added_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, full_name, int(is_super_admin), perms, added_by))
        await conn.commit()
        return await self.get_admin(telegram_id)

    async def get_all_admins(self) -> List[Admin]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM admins ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            admins = []
            for row in rows:
                data = dict(row)
                data['is_super_admin'] = bool(data['is_super_admin'])
                data['permissions'] = json.loads(data['permissions'])
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                admins.append(Admin(**data))
            return admins

    async def update_admin(self, telegram_id: int, **kwargs) -> Optional[Admin]:
        """Update admin permissions or other fields."""
        if not kwargs:
            return await self.get_admin(telegram_id)
        if 'permissions' in kwargs:
            kwargs['permissions'] = json.dumps(kwargs['permissions'])
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]
        conn = await self._get_connection()
        await conn.execute(f"UPDATE admins SET {set_clause} WHERE telegram_id = ?", values)
        await conn.commit()
        return await self.get_admin(telegram_id)

    async def delete_admin(self, telegram_id: int) -> bool:
        """Delete admin by telegram_id."""
        conn = await self._get_connection()
        cursor = await conn.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
        await conn.commit()
        return cursor.rowcount > 0

    # ============ CHANNEL METHODS ============
    async def get_channel(self, channel_id: int) -> Optional[Channel]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['is_mandatory'] = bool(data['is_mandatory'])
                data['is_poll_channel'] = bool(data['is_poll_channel'])
                data['is_active'] = bool(data['is_active'])
                data['channel_type'] = data.get('channel_type', 'telegram_channel') or 'telegram_channel'
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                return Channel(**data)
            return None

    async def create_channel(self, channel_id: int, title: str, username: str = None,
                             channel_type: str = "telegram_channel",
                             is_mandatory: bool = False, is_poll_channel: bool = True,
                             added_by: int = 0) -> Channel:
        conn = await self._get_connection()
        await conn.execute('''
            INSERT INTO channels (channel_id, username, title, channel_type, is_mandatory, is_poll_channel, added_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (channel_id, username, title, channel_type, int(is_mandatory), int(is_poll_channel), added_by))
        await conn.commit()
        return await self.get_channel(channel_id)

    async def update_channel(self, channel_id: int, **kwargs) -> Optional[Channel]:
        if not kwargs:
            return await self.get_channel(channel_id)
        for k, v in kwargs.items():
            if isinstance(v, bool):
                kwargs[k] = int(v)
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [channel_id]
        conn = await self._get_connection()
        await conn.execute(f"UPDATE channels SET {set_clause} WHERE channel_id = ?", values)
        await conn.commit()
        return await self.get_channel(channel_id)

    async def delete_channel(self, channel_id: int) -> bool:
        conn = await self._get_connection()
        cursor = await conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await conn.commit()
        return cursor.rowcount > 0

    async def get_all_channels(self, include_inactive: bool = True) -> List[Channel]:
        """Get all channels. Set include_inactive=False to only get active channels."""
        conn = await self._get_connection()
        if include_inactive:
            query = "SELECT * FROM channels ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM channels WHERE is_active = 1 ORDER BY created_at DESC"
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            channels = []
            for row in rows:
                data = dict(row)
                data['is_mandatory'] = bool(data['is_mandatory'])
                data['is_poll_channel'] = bool(data['is_poll_channel'])
                data['is_active'] = bool(data['is_active'])
                data['channel_type'] = data.get('channel_type', 'telegram_channel') or 'telegram_channel'
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                channels.append(Channel(**data))
            return channels

    async def get_mandatory_channels(self) -> List[Channel]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM channels WHERE is_mandatory = 1 AND is_active = 1") as cursor:
            rows = await cursor.fetchall()
            channels = []
            for row in rows:
                data = dict(row)
                data['is_mandatory'] = bool(data['is_mandatory'])
                data['is_poll_channel'] = bool(data['is_poll_channel'])
                data['is_active'] = bool(data['is_active'])
                data['channel_type'] = data.get('channel_type', 'telegram_channel') or 'telegram_channel'
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                channels.append(Channel(**data))
            return channels

    async def get_poll_channels(self) -> List[Channel]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM channels WHERE is_poll_channel = 1 AND is_active = 1") as cursor:
            rows = await cursor.fetchall()
            channels = []
            for row in rows:
                data = dict(row)
                data['is_mandatory'] = bool(data['is_mandatory'])
                data['is_poll_channel'] = bool(data['is_poll_channel'])
                data['is_active'] = bool(data['is_active'])
                data['channel_type'] = data.get('channel_type', 'telegram_channel') or 'telegram_channel'
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                channels.append(Channel(**data))
            return channels

    # ============ POLL METHODS ============
    async def create_poll(self, channel_id: int, name: str, text: str, created_by: int,
                          media_type: str = None, media_id: str = None,
                          button_layout: int = 1, results_visibility: str = "realtime",
                          scheduled_at: datetime = None, ends_at: datetime = None,
                          end_votes_count: int = None) -> Poll:
        conn = await self._get_connection()
        scheduled_str = scheduled_at.isoformat() if scheduled_at else None
        ends_str = ends_at.isoformat() if ends_at else None
        cursor = await conn.execute('''
            INSERT INTO polls (channel_id, name, text, media_type, media_id,
                button_layout, results_visibility, scheduled_at, ends_at,
                end_votes_count, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (channel_id, name, text, media_type, media_id, button_layout,
            results_visibility, scheduled_str, ends_str, end_votes_count, created_by))
        await conn.commit()
        poll_id = cursor.lastrowid
        return await self.get_poll(poll_id)

    async def get_poll(self, poll_id: int) -> Optional[Poll]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None
                data['ends_at'] = datetime.fromisoformat(data['ends_at']) if data['ends_at'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                return Poll(**data)
            return None

    async def update_poll(self, poll_id: int, **kwargs) -> Optional[Poll]:
        if not kwargs:
            return await self.get_poll(poll_id)
        for k, v in kwargs.items():
            if isinstance(v, datetime):
                kwargs[k] = v.isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [poll_id]
        conn = await self._get_connection()
        await conn.execute(f"UPDATE polls SET {set_clause} WHERE id = ?", values)
        await conn.commit()
        return await self.get_poll(poll_id)

    async def get_active_polls(self) -> List[Poll]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM polls WHERE status = 'active' ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            polls = []
            for row in rows:
                data = dict(row)
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None
                data['ends_at'] = datetime.fromisoformat(data['ends_at']) if data['ends_at'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                polls.append(Poll(**data))
            return polls

    async def get_polls_by_status(self, status: str) -> List[Poll]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM polls WHERE status = ? ORDER BY created_at DESC", (status,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for row in rows:
                data = dict(row)
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None
                data['ends_at'] = datetime.fromisoformat(data['ends_at']) if data['ends_at'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                polls.append(Poll(**data))
            return polls

    async def get_scheduled_polls(self) -> List[Poll]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM polls WHERE status = 'scheduled' AND scheduled_at <= datetime('now') ORDER BY scheduled_at ASC") as cursor:
            rows = await cursor.fetchall()
            polls = []
            for row in rows:
                data = dict(row)
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None
                data['ends_at'] = datetime.fromisoformat(data['ends_at']) if data['ends_at'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                polls.append(Poll(**data))
            return polls

    async def get_polls_count(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM polls") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_active_polls_count(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM polls WHERE status = 'active'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_expired_polls(self) -> List[Poll]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM polls WHERE status = 'active' AND ends_at IS NOT NULL AND ends_at <= datetime('now')") as cursor:
            rows = await cursor.fetchall()
            polls = []
            for row in rows:
                data = dict(row)
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None
                data['ends_at'] = datetime.fromisoformat(data['ends_at']) if data['ends_at'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                polls.append(Poll(**data))
            return polls

    # ============ POLL OPTIONS METHODS ============
    async def create_poll_option(self, poll_id: int, name: str, position: int, photo_id: str = None) -> PollOption:
        conn = await self._get_connection()
        cursor = await conn.execute('''
            INSERT INTO poll_options (poll_id, name, photo_id, position)
            VALUES (?, ?, ?, ?)
        ''', (poll_id, name, photo_id, position))
        await conn.commit()
        option_id = cursor.lastrowid
        async with conn.execute("SELECT * FROM poll_options WHERE id = ?", (option_id,)) as cursor:
            row = await cursor.fetchone()
            return PollOption(**dict(row))

    async def get_poll_options(self, poll_id: int) -> List[PollOption]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY position", (poll_id,)) as cursor:
            rows = await cursor.fetchall()
            return [PollOption(**dict(row)) for row in rows]

    async def increment_option_votes(self, option_id: int) -> None:
        conn = await self._get_connection()
        await conn.execute("UPDATE poll_options SET votes_count = votes_count + 1 WHERE id = ?", (option_id,))
        await conn.commit()

    # ============ VOTE METHODS ============
    async def create_vote(self, poll_id: int, option_id: int, user_id: int) -> Optional[Vote]:
        try:
            conn = await self._get_connection()
            cursor = await conn.execute('''
                INSERT INTO votes (poll_id, option_id, user_id)
                VALUES (?, ?, ?)
            ''', (poll_id, option_id, user_id))
            await conn.commit()
            vote_id = cursor.lastrowid
            await self.increment_option_votes(option_id)
            async with conn.execute("SELECT * FROM votes WHERE id = ?", (vote_id,)) as cursor:
                row = await cursor.fetchone()
                data = dict(row)
                data['voted_at'] = datetime.fromisoformat(data['voted_at']) if data['voted_at'] else datetime.now()
                return Vote(**data)
        except aiosqlite.IntegrityError:
            return None

    async def get_user_vote(self, poll_id: int, user_id: int) -> Optional[Vote]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['voted_at'] = datetime.fromisoformat(data['voted_at']) if data['voted_at'] else datetime.now()
                return Vote(**data)
            return None

    async def get_total_votes_count(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM votes") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_votes_count_today(self) -> int:
        conn = await self._get_connection()
        async with conn.execute("SELECT COUNT(*) FROM votes WHERE date(voted_at) = date('now')") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_poll_report_data(self, poll_id: int) -> List[dict]:
        """Get detailed voting data for a poll report."""
        conn = await self._get_connection()
        async with conn.execute('''
            SELECT
                u.full_name,
                u.username,
                u.phone,
                u.created_at as registered_at,
                v.voted_at,
                po.name as option_name
            FROM votes v
            JOIN users u ON v.user_id = u.id
            JOIN poll_options po ON v.option_id = po.id
            WHERE v.poll_id = ?
            ORDER BY v.voted_at DESC
        ''', (poll_id,)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data['registered_at'] = datetime.fromisoformat(data['registered_at']) if data['registered_at'] else None
                data['voted_at'] = datetime.fromisoformat(data['voted_at']) if data['voted_at'] else None
                result.append(data)
            return result

    async def get_user_active_votes_in_channel(self, telegram_id: int, channel_id: int) -> List[dict]:
        """Get user's votes in active polls for a specific channel."""
        conn = await self._get_connection()
        async with conn.execute('''
            SELECT v.id as vote_id, v.poll_id, v.option_id, p.name as poll_name,
                   p.channel_id, p.message_id, po.name as option_name
            FROM votes v
            JOIN users u ON v.user_id = u.id
            JOIN polls p ON v.poll_id = p.id
            JOIN poll_options po ON v.option_id = po.id
            WHERE u.telegram_id = ? AND p.channel_id = ? AND p.status = 'active'
        ''', (telegram_id, channel_id)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def cancel_vote(self, vote_id: int, option_id: int) -> bool:
        """Cancel a vote and decrement the option vote count."""
        conn = await self._get_connection()
        # Delete the vote
        cursor = await conn.execute("DELETE FROM votes WHERE id = ?", (vote_id,))
        if cursor.rowcount > 0:
            # Decrement the option vote count
            await conn.execute(
                "UPDATE poll_options SET votes_count = MAX(0, votes_count - 1) WHERE id = ?",
                (option_id,)
            )
            await conn.commit()
            return True
        return False

    async def get_user_votes_history(self, telegram_id: int) -> List[dict]:
        conn = await self._get_connection()
        async with conn.execute('''
            SELECT p.name as poll_name, po.name as option_name, v.voted_at
            FROM votes v
            JOIN polls p ON v.poll_id = p.id
            JOIN poll_options po ON v.option_id = po.id
            JOIN users u ON v.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY v.voted_at DESC
            LIMIT 20
        ''', (telegram_id,)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data['voted_at'] = datetime.fromisoformat(data['voted_at']) if data['voted_at'] else None
                result.append(data)
            return result

    # ============ CAPTCHA METHODS ============
    async def create_captcha(self, user_id: int, correct_answer: str) -> CaptchaAttempt:
        conn = await self._get_connection()
        await conn.execute("DELETE FROM captcha_attempts WHERE user_id = ?", (user_id,))
        cursor = await conn.execute('''
            INSERT INTO captcha_attempts (user_id, correct_answer)
            VALUES (?, ?)
        ''', (user_id, correct_answer))
        await conn.commit()
        captcha_id = cursor.lastrowid
        async with conn.execute("SELECT * FROM captcha_attempts WHERE id = ?", (captcha_id,)) as cursor:
            row = await cursor.fetchone()
            data = dict(row)
            data['is_passed'] = bool(data['is_passed'])
            data['blocked_until'] = datetime.fromisoformat(data['blocked_until']) if data['blocked_until'] else None
            data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
            return CaptchaAttempt(**data)

    async def get_captcha(self, user_id: int) -> Optional[CaptchaAttempt]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM captcha_attempts WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['is_passed'] = bool(data['is_passed'])
                data['blocked_until'] = datetime.fromisoformat(data['blocked_until']) if data['blocked_until'] else None
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                return CaptchaAttempt(**data)
            return None

    async def update_captcha_attempts(self, user_id: int, attempts: int,
                                       is_passed: bool = False,
                                       blocked_until: datetime = None) -> None:
        blocked_str = blocked_until.isoformat() if blocked_until else None
        conn = await self._get_connection()
        await conn.execute('''
            UPDATE captcha_attempts
            SET attempts = ?, is_passed = ?, blocked_until = ?
            WHERE user_id = ?
        ''', (attempts, int(is_passed), blocked_str, user_id))
        await conn.commit()

    # ============ SCHEDULED POSTS METHODS ============
    async def create_scheduled_post(self, channels: List[int], text: str, created_by: int,
                                     media_type: str = None, media_id: str = None,
                                     buttons: str = None, scheduled_at: datetime = None,
                                     repeat_type: str = "once") -> ScheduledPost:
        conn = await self._get_connection()
        channels_json = json.dumps(channels)
        scheduled_str = scheduled_at.isoformat() if scheduled_at else datetime.now().isoformat()
        cursor = await conn.execute('''
            INSERT INTO scheduled_posts (channels, text, media_type, media_id,
                buttons, scheduled_at, repeat_type, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (channels_json, text, media_type, media_id, buttons, scheduled_str, repeat_type, created_by))
        await conn.commit()
        post_id = cursor.lastrowid
        return await self.get_scheduled_post(post_id)

    async def get_scheduled_post(self, post_id: int) -> Optional[ScheduledPost]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else datetime.now()
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                return ScheduledPost(**data)
            return None

    async def update_scheduled_post(self, post_id: int, **kwargs) -> Optional[ScheduledPost]:
        if not kwargs:
            return await self.get_scheduled_post(post_id)
        if 'channels' in kwargs:
            kwargs['channels'] = json.dumps(kwargs['channels'])
        if 'scheduled_at' in kwargs and isinstance(kwargs['scheduled_at'], datetime):
            kwargs['scheduled_at'] = kwargs['scheduled_at'].isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [post_id]
        conn = await self._get_connection()
        await conn.execute(f"UPDATE scheduled_posts SET {set_clause} WHERE id = ?", values)
        await conn.commit()
        return await self.get_scheduled_post(post_id)

    async def delete_scheduled_post(self, post_id: int) -> bool:
        conn = await self._get_connection()
        cursor = await conn.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        await conn.commit()
        return cursor.rowcount > 0

    async def get_pending_scheduled_posts(self) -> List[ScheduledPost]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= datetime('now') ORDER BY scheduled_at ASC") as cursor:
            rows = await cursor.fetchall()
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else datetime.now()
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                posts.append(ScheduledPost(**data))
            return posts

    async def get_scheduled_posts_by_status(self, status: str) -> List[ScheduledPost]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM scheduled_posts WHERE status = ? ORDER BY scheduled_at DESC", (status,)) as cursor:
            rows = await cursor.fetchall()
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else datetime.now()
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                posts.append(ScheduledPost(**data))
            return posts

    async def get_all_scheduled_posts(self, limit: int = 50) -> List[ScheduledPost]:
        conn = await self._get_connection()
        async with conn.execute("SELECT * FROM scheduled_posts ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            posts = []
            for row in rows:
                data = dict(row)
                data['channels'] = json.loads(data['channels'])
                data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else datetime.now()
                data['created_at'] = datetime.fromisoformat(data['created_at']) if data['created_at'] else datetime.now()
                posts.append(ScheduledPost(**data))
            return posts


db = Database()

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class User:
    id: int = 0
    telegram_id: int = 0
    username: Optional[str] = None
    full_name: str = ""
    phone: Optional[str] = None
    language: str = "uz"
    is_blocked: bool = False
    spam_score: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Admin:
    id: int = 0
    telegram_id: int = 0
    username: Optional[str] = None
    full_name: str = ""
    is_super_admin: bool = False
    permissions: List[str] = field(default_factory=list)
    added_by: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Channel:
    id: int = 0
    channel_id: int = 0
    username: Optional[str] = None
    title: str = ""
    is_mandatory: bool = False
    is_poll_channel: bool = True
    is_active: bool = True
    added_by: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Poll:
    id: int = 0
    channel_id: int = 0
    message_id: Optional[int] = None
    name: str = ""
    text: str = ""
    media_type: Optional[str] = None  # photo, video
    media_id: Optional[str] = None
    button_layout: int = 1  # 1, 2, 3 per row
    results_visibility: str = "realtime"  # realtime, after_finish, admins_only
    status: str = "draft"  # draft, scheduled, active, paused, finished
    scheduled_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    end_votes_count: Optional[int] = None
    created_by: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PollOption:
    id: int = 0
    poll_id: int = 0
    name: str = ""
    photo_id: Optional[str] = None
    position: int = 0
    votes_count: int = 0


@dataclass
class Vote:
    id: int = 0
    poll_id: int = 0
    option_id: int = 0
    user_id: int = 0
    voted_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScheduledPost:
    id: int = 0
    channels: List[int] = field(default_factory=list)
    text: str = ""
    media_type: Optional[str] = None
    media_id: Optional[str] = None
    buttons: Optional[str] = None  # JSON string
    scheduled_at: datetime = field(default_factory=datetime.now)
    repeat_type: str = "once"  # once, daily, weekly
    status: str = "pending"  # pending, sent, cancelled
    created_by: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CaptchaAttempt:
    id: int = 0
    user_id: int = 0
    correct_answer: str = ""
    attempts: int = 0
    is_passed: bool = False
    blocked_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

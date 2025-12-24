import re
from datetime import datetime, timedelta
from typing import Optional
from aiogram.types import User as TgUser

from app.config import SPAM_BLOCK_THRESHOLD


def calculate_spam_score(user: TgUser, account_created: Optional[datetime] = None) -> int:
    """
    Calculate spam score based on user profile.

    Criteria:
    - Account age < 7 days: 1 point
    - No profile photo: 1 point (checked separately)
    - No username: 1 point
    - Suspicious name pattern: 1 point
    """
    score = 0

    # Check username
    if not user.username:
        score += 1

    # Check suspicious name patterns (e.g., User123456)
    if user.first_name:
        name = user.first_name + (user.last_name or "")
        # Pattern like User123456 or random letters/numbers
        if re.match(r'^[A-Za-z]+\d{4,}$', name):
            score += 1
        # Very short generic names
        if len(name) <= 2:
            score += 1

    # Account age check (if we have creation date)
    if account_created:
        if datetime.now() - account_created < timedelta(days=7):
            score += 1

    return score


def is_suspicious_voting(vote_time_seconds: float) -> int:
    """
    Check if voting was too fast (bot behavior).
    Returns additional spam points.
    """
    if vote_time_seconds < 3:
        return 2  # Very suspicious - voted in less than 3 seconds
    return 0


def should_block_user(spam_score: int) -> bool:
    """Check if user should be blocked based on spam score."""
    return spam_score >= SPAM_BLOCK_THRESHOLD


def validate_full_name(name: str) -> bool:
    """
    Validate full name.
    - Minimum 2 words
    - Only letters and spaces
    - No numbers or special characters
    """
    if not name or not name.strip():
        return False

    # Remove extra spaces
    name = ' '.join(name.split())

    # Check minimum 2 words
    words = name.split()
    if len(words) < 2:
        return False

    # Check only letters (including Cyrillic and Latin)
    # Allow apostrophe for names like O'zbekiston
    pattern = r"^[a-zA-Zа-яА-ЯёЁўЎқҚғҒҳҲ\s']+$"
    if not re.match(pattern, name):
        return False

    # Each word should have at least 2 characters
    for word in words:
        if len(word.replace("'", "")) < 2:
            return False

    return True


def format_phone_number(phone: str) -> str:
    """Format phone number to +998XXXXXXXXX format."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # If starts with 998, add +
    if digits.startswith('998'):
        return f"+{digits}"

    # If starts with 8 (old format), replace with +998
    if digits.startswith('8') and len(digits) == 10:
        return f"+998{digits[1:]}"

    # If 9 digits (without country code)
    if len(digits) == 9:
        return f"+998{digits}"

    return f"+{digits}"

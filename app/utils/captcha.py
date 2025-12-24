import random
from datetime import datetime, timedelta
from typing import Tuple

from app.config import CAPTCHA_MAX_ATTEMPTS, BLOCK_DURATION_MINUTES


def generate_captcha() -> Tuple[str, str]:
    """
    Generate a simple math captcha.
    Returns: (question, answer)
    """
    operations = ['+', '-', '*']
    op = random.choice(operations)

    if op == '+':
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        answer = a + b
        question = f"{a} + {b} = ?"
    elif op == '-':
        a = random.randint(10, 50)
        b = random.randint(1, a)  # Ensure positive result
        answer = a - b
        question = f"{a} - {b} = ?"
    else:  # multiplication
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        answer = a * b
        question = f"{a} × {b} = ?"

    return question, str(answer)


def generate_code_captcha() -> Tuple[str, str]:
    """
    Generate a random code captcha (4-6 digits).
    Returns: (code_to_show, code_to_enter)
    """
    length = random.randint(4, 6)
    code = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return code, code


def check_captcha_answer(user_answer: str, correct_answer: str) -> bool:
    """Check if user's answer matches the correct answer."""
    return user_answer.strip() == correct_answer.strip()


def get_block_until() -> datetime:
    """Get the datetime until which user should be blocked."""
    return datetime.now() + timedelta(minutes=BLOCK_DURATION_MINUTES)


def is_blocked(blocked_until: datetime) -> bool:
    """Check if user is still blocked."""
    if blocked_until is None:
        return False
    return datetime.now() < blocked_until


def get_remaining_attempts(current_attempts: int) -> int:
    """Get remaining captcha attempts."""
    return max(0, CAPTCHA_MAX_ATTEMPTS - current_attempts)

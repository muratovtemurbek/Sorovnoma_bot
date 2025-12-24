import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", 0))

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "sorovnoma_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Anti-spam settings
SPAM_BLOCK_THRESHOLD = 3
BLOCK_DURATION_MINUTES = 5
MAX_MESSAGES_PER_MINUTE = 5
MAX_VOTES_PER_MINUTE = 3
CAPTCHA_MAX_ATTEMPTS = 3

# Admin permissions
PERMISSIONS = {
    "manage_channels": "Kanallarni boshqarish",
    "create_poll": "Sorovnoma yaratish",
    "manage_poll": "Sorovnomalarni boshqarish",
    "schedule_post": "Post rejalashtirish",
    "view_users": "Foydalanuvchilar ro'yxati",
    "export_data": "Excel export",
    "manage_admins": "Adminlarni boshqarish",
    "view_stats": "Statistikani ko'rish",
    "block_users": "Foydalanuvchilarni bloklash",
}

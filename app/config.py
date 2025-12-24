import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Super Admin IDs (comma separated in .env)
_super_admin_ids = os.getenv("SUPER_ADMIN_ID", "")
SUPER_ADMIN_IDS = [int(x.strip()) for x in _super_admin_ids.split(",") if x.strip().isdigit()]
SUPER_ADMIN_ID = SUPER_ADMIN_IDS[0] if SUPER_ADMIN_IDS else 0

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

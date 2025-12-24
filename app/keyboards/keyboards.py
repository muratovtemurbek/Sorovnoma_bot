from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from typing import List, Optional
from app.locales.texts import get_text
from app.database.models import Channel, PollOption


def language_keyboard() -> InlineKeyboardMarkup:
    """Language selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ]
    ])


def subscription_keyboard(channels: List[Channel], lang: str = "uz") -> InlineKeyboardMarkup:
    """Mandatory subscription channels keyboard."""
    buttons = []
    for channel in channels:
        if channel.username:
            url = f"https://t.me/{channel.username.lstrip('@')}"
        else:
            url = f"https://t.me/c/{str(channel.channel_id)[4:]}"
        buttons.append([InlineKeyboardButton(text=channel.title, url=url)])

    buttons.append([InlineKeyboardButton(
        text=f"✅ {get_text('check_subscription', lang)}",
        callback_data="check_subscription"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def phone_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Phone number request keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text=f"📱 {get_text('share_phone_btn', lang)}",
                request_contact=True
            )]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """User main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"📊 {get_text('active_polls', lang)}")],
            [KeyboardButton(text=f"📈 {get_text('my_votes', lang)}")],
            [
                KeyboardButton(text=f"⚙️ {get_text('settings', lang)}"),
                KeyboardButton(text=f"ℹ️ {get_text('help', lang)}")
            ]
        ],
        resize_keyboard=True
    )


def settings_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Settings keyboard with language options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 " + get_text("choose_language", lang),
                               callback_data="change_language")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_to_menu")]
    ])


def back_keyboard(lang: str = "uz", callback: str = "back") -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}", callback_data=callback)]
    ])


def confirm_cancel_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Confirm/Cancel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ {get_text('confirm', lang)}", callback_data="confirm"),
            InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}", callback_data="cancel"),
        ]
    ])


def skip_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Skip button keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏭ {get_text('skip', lang)}", callback_data="skip")]
    ])


def option_continue_keyboard(options_count: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Continue or stop adding options keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ Davom etish ({options_count} ta nomzod)", callback_data="option_continue")],
        [InlineKeyboardButton(text=f"✅ To'xtatish va davom etish", callback_data="option_stop")],
        [InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}", callback_data="cancel_poll")]
    ])


# ============ ADMIN KEYBOARDS ============

def admin_menu_keyboard(lang: str = "uz", is_super: bool = False) -> ReplyKeyboardMarkup:
    """Admin main menu keyboard."""
    keyboard = [
        [KeyboardButton(text=f"📢 {get_text('channels', lang)}"),
         KeyboardButton(text=f"📊 {get_text('polls', lang)}")],
        [KeyboardButton(text=f"📝 {get_text('posts', lang)}"),
         KeyboardButton(text=f"👥 {get_text('users', lang)}")],
        [KeyboardButton(text=f"📈 {get_text('statistics', lang)}")]
    ]

    if is_super:
        keyboard.insert(-1, [KeyboardButton(text=f"👨‍💼 {get_text('admins', lang)}"),
                              KeyboardButton(text=f"⚙️ {get_text('settings_admin', lang)}")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def channels_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Channels management menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ {get_text('add_channel', lang)}",
                               callback_data="add_channel")],
        [InlineKeyboardButton(text=f"📋 {get_text('channel_list', lang)}",
                               callback_data="channel_list")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


def channel_list_keyboard(channels: List[Channel], lang: str = "uz") -> InlineKeyboardMarkup:
    """List of channels keyboard."""
    buttons = []
    for channel in channels:
        status = "✅" if channel.is_active else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {channel.title}",
            callback_data=f"channel_{channel.channel_id}"
        )])
    buttons.append([InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                                          callback_data="channels_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_settings_keyboard(channel: Channel, lang: str = "uz") -> InlineKeyboardMarkup:
    """Individual channel settings."""
    mandatory = "✅" if channel.is_mandatory else "❌"
    poll_ch = "✅" if channel.is_poll_channel else "❌"
    active = "✅" if channel.is_active else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{mandatory} {get_text('mandatory_sub', lang)}",
            callback_data=f"toggle_mandatory_{channel.channel_id}"
        )],
        [InlineKeyboardButton(
            text=f"{poll_ch} {get_text('poll_channel', lang)}",
            callback_data=f"toggle_poll_{channel.channel_id}"
        )],
        [InlineKeyboardButton(
            text=f"{active} Faol",
            callback_data=f"toggle_active_{channel.channel_id}"
        )],
        [InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=f"delete_channel_{channel.channel_id}"
        )],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="channel_list")]
    ])


def polls_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Polls management menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ {get_text('new_poll', lang)}",
                               callback_data="new_poll")],
        [InlineKeyboardButton(text=f"📊 {get_text('active_polls_admin', lang)}",
                               callback_data="active_polls")],
        [InlineKeyboardButton(text=f"✅ {get_text('finished_polls', lang)}",
                               callback_data="finished_polls")],
        [InlineKeyboardButton(text=f"📝 {get_text('drafts', lang)}",
                               callback_data="draft_polls")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


def select_channel_keyboard(channels: List[Channel], lang: str = "uz") -> InlineKeyboardMarkup:
    """Select channel for poll."""
    buttons = [[InlineKeyboardButton(
        text=channel.title,
        callback_data=f"poll_channel_{channel.channel_id}"
    )] for channel in channels]
    buttons.append([InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                                          callback_data="cancel_poll")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def content_type_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select content type for poll."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📝 {get_text('text_only', lang)}",
                               callback_data="content_text")],
        [InlineKeyboardButton(text=f"📷 {get_text('photo_text', lang)}",
                               callback_data="content_photo")],
        [InlineKeyboardButton(text=f"🎥 {get_text('video_text', lang)}",
                               callback_data="content_video")],
        [InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                               callback_data="cancel_poll")]
    ])


def button_layout_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select button layout."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("one_per_row", lang),
                               callback_data="layout_1")],
        [InlineKeyboardButton(text=get_text("two_per_row", lang),
                               callback_data="layout_2")],
        [InlineKeyboardButton(text=get_text("three_per_row", lang),
                               callback_data="layout_3")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_poll_step")]
    ])


def start_time_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select start time."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"▶️ {get_text('start_now', lang)}",
                               callback_data="start_now")],
        [InlineKeyboardButton(text=f"📅 {get_text('schedule', lang)}",
                               callback_data="schedule_poll")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_poll_step")]
    ])


def end_condition_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select end condition."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏰ {get_text('end_at_time', lang)}",
                               callback_data="end_time")],
        [InlineKeyboardButton(text=f"🗳 {get_text('end_at_votes', lang)}",
                               callback_data="end_votes")],
        [InlineKeyboardButton(text=f"✋ {get_text('end_manually', lang)}",
                               callback_data="end_manual")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_poll_step")]
    ])


def results_visibility_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select results visibility."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📊 {get_text('realtime', lang)}",
                               callback_data="visibility_realtime")],
        [InlineKeyboardButton(text=f"🔒 {get_text('after_finish', lang)}",
                               callback_data="visibility_after")],
        [InlineKeyboardButton(text=f"👨‍💼 {get_text('admins_only', lang)}",
                               callback_data="visibility_admins")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_poll_step")]
    ])


def poll_preview_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Poll preview confirmation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {get_text('confirm', lang)}",
                               callback_data="confirm_poll")],
        [InlineKeyboardButton(text=f"✏️ Tahrirlash",
                               callback_data="edit_poll")],
        [InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                               callback_data="cancel_poll")]
    ])


def poll_options_keyboard(poll_id: int, options: List[PollOption],
                           layout: int = 1, show_results: bool = True) -> InlineKeyboardMarkup:
    """Generate poll voting buttons."""
    buttons = []
    row = []

    total_votes = sum(opt.votes_count for opt in options)

    for i, option in enumerate(options):
        if show_results and total_votes > 0:
            percentage = (option.votes_count / total_votes) * 100
            text = f"{option.name} - {option.votes_count} ({percentage:.1f}%)"
        else:
            text = option.name

        btn = InlineKeyboardButton(
            text=text,
            callback_data=f"vote_{poll_id}_{option.id}"
        )
        row.append(btn)

        if len(row) >= layout:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def poll_manage_keyboard(poll_id: int, status: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Poll management buttons for admin."""
    buttons = []

    if status == "active":
        buttons.append([InlineKeyboardButton(text="⏸ To'xtatish",
                                              callback_data=f"pause_poll_{poll_id}")])
        buttons.append([InlineKeyboardButton(text="🛑 Tugatish",
                                              callback_data=f"finish_poll_{poll_id}")])
    elif status == "paused":
        buttons.append([InlineKeyboardButton(text="▶️ Davom ettirish",
                                              callback_data=f"resume_poll_{poll_id}")])
        buttons.append([InlineKeyboardButton(text="🛑 Tugatish",
                                              callback_data=f"finish_poll_{poll_id}")])
    elif status == "draft":
        buttons.append([InlineKeyboardButton(text="▶️ Joylash",
                                              callback_data=f"publish_poll_{poll_id}")])
        buttons.append([InlineKeyboardButton(text="🗑 O'chirish",
                                              callback_data=f"delete_poll_{poll_id}")])

    buttons.append([InlineKeyboardButton(text="📊 Hisobot (Excel)",
                                          callback_data=f"export_poll_{poll_id}")])
    buttons.append([InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                                          callback_data="polls_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Users management
def users_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Users management menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📋 {get_text('users_list', lang)}",
                               callback_data="users_list")],
        [InlineKeyboardButton(text=f"🔍 {get_text('search_user', lang)}",
                               callback_data="search_user")],
        [InlineKeyboardButton(text=f"🚫 {get_text('blocked_users', lang)}",
                               callback_data="blocked_users")],
        [InlineKeyboardButton(text=f"📥 {get_text('export_users', lang)}",
                               callback_data="export_users")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


def pagination_keyboard(current: int, total: int, prefix: str,
                         lang: str = "uz") -> InlineKeyboardMarkup:
    """Pagination keyboard."""
    buttons = []
    row = []

    if current > 0:
        row.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_{current-1}"))

    row.append(InlineKeyboardButton(text=f"{current+1}/{total}", callback_data="noop"))

    if current < total - 1:
        row.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_{current+1}"))

    buttons.append(row)
    buttons.append([InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                                          callback_data="users_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def user_actions_keyboard(user_id: int, is_blocked: bool, lang: str = "uz") -> InlineKeyboardMarkup:
    """User action buttons."""
    block_text = get_text("unblock_user", lang) if is_blocked else get_text("block_user", lang)
    block_action = "unblock" if is_blocked else "block"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚫 {block_text}",
                               callback_data=f"{block_action}_user_{user_id}")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="users_list")]
    ])


# Admins management
def admins_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Admins management menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ {get_text('add_admin', lang)}",
                               callback_data="add_admin")],
        [InlineKeyboardButton(text=f"📋 {get_text('admin_list', lang)}",
                               callback_data="admin_list")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


def permissions_keyboard(current_perms: List[str], lang: str = "uz") -> InlineKeyboardMarkup:
    """Permissions selection keyboard."""
    from app.config import PERMISSIONS

    buttons = []
    for perm_code, perm_name in PERMISSIONS.items():
        check = "✅" if perm_code in current_perms else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{check} {perm_name}",
            callback_data=f"perm_{perm_code}"
        )])

    buttons.append([InlineKeyboardButton(text=f"✅ {get_text('confirm', lang)}",
                                          callback_data="confirm_permissions")])
    buttons.append([InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                                          callback_data="cancel_admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Statistics
def stats_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Statistics menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📊 {get_text('general_stats', lang)}",
                               callback_data="general_stats")],
        [InlineKeyboardButton(text=f"📅 {get_text('daily_stats', lang)}",
                               callback_data="daily_stats")],
        [InlineKeyboardButton(text=f"📆 {get_text('weekly_stats', lang)}",
                               callback_data="weekly_stats")],
        [InlineKeyboardButton(text=f"🗓 {get_text('monthly_stats', lang)}",
                               callback_data="monthly_stats")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


# Posts
def posts_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Posts management menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ {get_text('new_post', lang)}",
                               callback_data="new_post")],
        [InlineKeyboardButton(text=f"📅 {get_text('scheduled_posts', lang)}",
                               callback_data="scheduled_posts")],
        [InlineKeyboardButton(text=f"✅ {get_text('sent_posts', lang)}",
                               callback_data="sent_posts")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="admin_back")]
    ])


def select_channels_keyboard(channels: List[Channel], selected: List[int],
                              lang: str = "uz") -> InlineKeyboardMarkup:
    """Select multiple channels for post."""
    buttons = []
    for channel in channels:
        check = "✅" if channel.channel_id in selected else "⬜"
        buttons.append([InlineKeyboardButton(
            text=f"{check} {channel.title}",
            callback_data=f"post_ch_{channel.channel_id}"
        )])

    buttons.append([InlineKeyboardButton(text=f"✅ {get_text('confirm', lang)}",
                                          callback_data="confirm_channels")])
    buttons.append([InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                                          callback_data="cancel_post")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def post_content_type_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select content type for post."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📝 {get_text('text_only', lang)}",
                               callback_data="post_content_text")],
        [InlineKeyboardButton(text=f"📷 {get_text('photo_text', lang)}",
                               callback_data="post_content_photo")],
        [InlineKeyboardButton(text=f"🎥 {get_text('video_text', lang)}",
                               callback_data="post_content_video")],
        [InlineKeyboardButton(text=f"📄 Dokument + matn",
                               callback_data="post_content_document")],
        [InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                               callback_data="cancel_post")]
    ])


def post_time_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select send time for post."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"▶️ Hozir yuborish",
                               callback_data="post_send_now")],
        [InlineKeyboardButton(text=f"📅 Rejalashtirish",
                               callback_data="post_schedule")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_post_step")]
    ])


def post_repeat_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Select repeat type for post."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1️⃣ {get_text('once', lang)}",
                               callback_data="post_repeat_once")],
        [InlineKeyboardButton(text=f"📅 {get_text('daily', lang)}",
                               callback_data="post_repeat_daily")],
        [InlineKeyboardButton(text=f"📆 {get_text('weekly', lang)}",
                               callback_data="post_repeat_weekly")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_post_step")]
    ])


def post_buttons_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Ask about inline buttons for post."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Tugma qo'shish",
                               callback_data="add_post_button")],
        [InlineKeyboardButton(text="⏭ Tugmasiz davom etish",
                               callback_data="skip_post_buttons")],
        [InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                               callback_data="back_post_step")]
    ])


def post_preview_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Post preview confirmation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {get_text('confirm', lang)}",
                               callback_data="confirm_post")],
        [InlineKeyboardButton(text="✏️ Tahrirlash",
                               callback_data="edit_post")],
        [InlineKeyboardButton(text=f"❌ {get_text('cancel', lang)}",
                               callback_data="cancel_post")]
    ])


def scheduled_posts_list_keyboard(posts: list, lang: str = "uz") -> InlineKeyboardMarkup:
    """List of scheduled posts."""
    buttons = []
    for post in posts[:10]:  # Limit to 10 posts
        scheduled = post.scheduled_at.strftime("%d.%m %H:%M") if post.scheduled_at else "—"
        text_preview = post.text[:20] + "..." if len(post.text) > 20 else post.text
        buttons.append([InlineKeyboardButton(
            text=f"📅 {scheduled} | {text_preview}",
            callback_data=f"view_post_{post.id}"
        )])

    buttons.append([InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                                          callback_data="posts_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def post_actions_keyboard(post_id: int, status: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Post action buttons."""
    buttons = []

    if status == "pending":
        buttons.append([InlineKeyboardButton(text="▶️ Hozir yuborish",
                                              callback_data=f"send_post_now_{post_id}")])
        buttons.append([InlineKeyboardButton(text="✏️ Tahrirlash",
                                              callback_data=f"edit_post_{post_id}")])
        buttons.append([InlineKeyboardButton(text="🗑 O'chirish",
                                              callback_data=f"delete_post_{post_id}")])

    buttons.append([InlineKeyboardButton(text=f"◀️ {get_text('back', lang)}",
                                          callback_data="scheduled_posts")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

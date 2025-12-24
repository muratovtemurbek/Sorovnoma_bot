from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
import json

from app.database.database_sqlite import db
from app.states.states import (
    AdminChannelState, AdminPollState, AdminUserState, AdminAddAdminState, AdminPostState
)
from app.locales.texts import get_text
from app.keyboards.keyboards import (
    admin_menu_keyboard, channels_menu_keyboard, channel_list_keyboard,
    channel_settings_keyboard, polls_menu_keyboard, select_channel_keyboard,
    content_type_keyboard, button_layout_keyboard, start_time_keyboard,
    end_condition_keyboard, results_visibility_keyboard, poll_preview_keyboard,
    poll_options_keyboard, poll_manage_keyboard, users_menu_keyboard,
    pagination_keyboard, user_actions_keyboard, admins_menu_keyboard,
    permissions_keyboard, stats_menu_keyboard, posts_menu_keyboard,
    back_keyboard, skip_keyboard, select_channels_keyboard,
    post_content_type_keyboard, post_time_keyboard, post_repeat_keyboard,
    post_buttons_keyboard, post_preview_keyboard, scheduled_posts_list_keyboard,
    post_actions_keyboard
)
from app.utils.helpers import check_bot_admin, get_channel_info
from app.utils.excel import create_users_excel, create_poll_results_excel, create_statistics_excel
from app.config import SUPER_ADMIN_ID, SUPER_ADMIN_IDS, PERMISSIONS

router = Router()


# ============ MIDDLEWARE CHECK ============
async def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    admin = await db.get_admin(user_id)
    return admin is not None


async def has_permission(user_id: int, permission: str) -> bool:
    """Check if admin has specific permission."""
    admin = await db.get_admin(user_id)
    if not admin:
        return False
    if admin.is_super_admin:
        return True
    return permission in admin.permissions


# ============ ADMIN PANEL ============
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Show admin panel."""
    admin = await db.get_admin(message.from_user.id)

    if not admin:
        # Check if this is super admin first time
        if message.from_user.id in SUPER_ADMIN_IDS:
            admin = await db.create_admin(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                is_super_admin=True
            )
        else:
            await message.answer(get_text("no_permission", "uz"))
            return

    await message.answer(
        get_text("admin_panel", "uz"),
        reply_markup=admin_menu_keyboard("uz", admin.is_super_admin)
    )


# ============ CHANNELS MANAGEMENT ============
@router.message(F.text.contains("Kanallar") | F.text.contains("Каналы") | F.text.contains("Channels"))
async def channels_menu(message: Message):
    """Show channels menu."""
    if not await has_permission(message.from_user.id, "manage_channels"):
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"📢 {get_text('channels', 'uz')}",
        reply_markup=channels_menu_keyboard("uz")
    )


@router.callback_query(F.data == "channels_menu")
async def channels_menu_callback(callback: CallbackQuery):
    """Show channels menu via callback."""
    await callback.message.edit_text(
        f"📢 {get_text('channels', 'uz')}",
        reply_markup=channels_menu_keyboard("uz")
    )


@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Start adding a channel."""
    await callback.message.edit_text(
        get_text("enter_channel", "uz"),
        reply_markup=back_keyboard("uz", "channels_menu")
    )
    await state.set_state(AdminChannelState.waiting_channel)


@router.message(AdminChannelState.waiting_channel)
async def add_channel_process(message: Message, state: FSMContext, bot: Bot):
    """Process channel input."""
    channel_info = await get_channel_info(bot, message.text.strip())

    if not channel_info:
        await message.answer(get_text("channel_not_found", "uz"))
        return

    if not await check_bot_admin(bot, channel_info["channel_id"]):
        await message.answer(get_text("channel_not_found", "uz"))
        return

    # Check if channel already exists
    existing = await db.get_channel(channel_info["channel_id"])
    if existing:
        await message.answer("Kanal allaqachon qo'shilgan!")
        await state.clear()
        return

    # Add channel
    await db.create_channel(
        channel_id=channel_info["channel_id"],
        title=channel_info["title"],
        username=channel_info["username"],
        added_by=message.from_user.id
    )

    await message.answer(get_text("channel_added", "uz"))
    await state.clear()

    # Show channels menu
    await message.answer(
        f"📢 {get_text('channels', 'uz')}",
        reply_markup=channels_menu_keyboard("uz")
    )


@router.callback_query(F.data == "channel_list")
async def show_channel_list(callback: CallbackQuery):
    """Show list of channels."""
    channels = await db.get_all_channels()

    if not channels:
        await callback.answer("Kanallar yo'q", show_alert=True)
        return

    await callback.message.edit_text(
        get_text("channel_list", "uz"),
        reply_markup=channel_list_keyboard(channels, "uz")
    )


@router.callback_query(F.data.startswith("channel_"))
async def show_channel_settings(callback: CallbackQuery):
    """Show individual channel settings."""
    channel_id = int(callback.data.split("_")[1])
    channel = await db.get_channel(channel_id)

    if not channel:
        await callback.answer("Kanal topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"{get_text('channel_settings', 'uz')}\n\n{channel.title}",
        reply_markup=channel_settings_keyboard(channel, "uz")
    )


@router.callback_query(F.data.startswith("toggle_mandatory_"))
async def toggle_mandatory(callback: CallbackQuery):
    """Toggle mandatory subscription."""
    channel_id = int(callback.data.split("_")[2])
    channel = await db.get_channel(channel_id)

    if channel:
        await db.update_channel(channel_id, is_mandatory=not channel.is_mandatory)
        channel = await db.get_channel(channel_id)
        await callback.message.edit_reply_markup(
            reply_markup=channel_settings_keyboard(channel, "uz")
        )


@router.callback_query(F.data.startswith("toggle_poll_"))
async def toggle_poll_channel(callback: CallbackQuery):
    """Toggle poll channel status."""
    channel_id = int(callback.data.split("_")[2])
    channel = await db.get_channel(channel_id)

    if channel:
        await db.update_channel(channel_id, is_poll_channel=not channel.is_poll_channel)
        channel = await db.get_channel(channel_id)
        await callback.message.edit_reply_markup(
            reply_markup=channel_settings_keyboard(channel, "uz")
        )


@router.callback_query(F.data.startswith("toggle_active_"))
async def toggle_active(callback: CallbackQuery):
    """Toggle channel active status."""
    channel_id = int(callback.data.split("_")[2])
    channel = await db.get_channel(channel_id)

    if channel:
        await db.update_channel(channel_id, is_active=not channel.is_active)
        channel = await db.get_channel(channel_id)
        await callback.message.edit_reply_markup(
            reply_markup=channel_settings_keyboard(channel, "uz")
        )


@router.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel(callback: CallbackQuery):
    """Delete channel."""
    channel_id = int(callback.data.split("_")[2])
    await db.delete_channel(channel_id)
    await callback.answer(get_text("channel_deleted", "uz"))

    channels = await db.get_all_channels()
    if channels:
        await callback.message.edit_text(
            get_text("channel_list", "uz"),
            reply_markup=channel_list_keyboard(channels, "uz")
        )
    else:
        await callback.message.edit_text(
            f"📢 {get_text('channels', 'uz')}",
            reply_markup=channels_menu_keyboard("uz")
        )


# ============ POLLS MANAGEMENT ============
@router.message(F.text.contains("Sorovnomalar") | F.text.contains("Опросы") | F.text.contains("Polls"))
async def polls_menu(message: Message):
    """Show polls menu."""
    if not await has_permission(message.from_user.id, "manage_poll"):
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"📊 {get_text('polls', 'uz')}",
        reply_markup=polls_menu_keyboard("uz")
    )


@router.callback_query(F.data == "polls_menu")
async def polls_menu_callback(callback: CallbackQuery):
    """Show polls menu via callback."""
    await callback.message.edit_text(
        f"📊 {get_text('polls', 'uz')}",
        reply_markup=polls_menu_keyboard("uz")
    )


@router.callback_query(F.data == "active_polls")
async def active_polls_list(callback: CallbackQuery):
    """Show list of active polls."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    polls = await db.get_active_polls()
    if not polls:
        await callback.answer("Faol so'rovnomalar yo'q", show_alert=True)
        return

    buttons = []
    for poll in polls:
        options = await db.get_poll_options(poll.id)
        total_votes = sum(opt.votes_count for opt in options)
        buttons.append([InlineKeyboardButton(
            text=f"📊 {poll.name} ({total_votes} ovoz)",
            callback_data=f"view_poll_{poll.id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="polls_menu")])

    await callback.message.edit_text(
        "📊 Faol so'rovnomalar:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data == "finished_polls")
async def finished_polls_list(callback: CallbackQuery):
    """Show list of finished polls."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    polls = await db.get_polls_by_status("finished")
    if not polls:
        await callback.answer("Tugagan so'rovnomalar yo'q", show_alert=True)
        return

    buttons = []
    for poll in polls:
        options = await db.get_poll_options(poll.id)
        total_votes = sum(opt.votes_count for opt in options)
        buttons.append([InlineKeyboardButton(
            text=f"✅ {poll.name} ({total_votes} ovoz)",
            callback_data=f"view_poll_{poll.id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="polls_menu")])

    await callback.message.edit_text(
        "✅ Tugagan so'rovnomalar:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data == "draft_polls")
async def draft_polls_list(callback: CallbackQuery):
    """Show list of draft polls."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    polls = await db.get_polls_by_status("draft")
    if not polls:
        await callback.answer("Qoralama so'rovnomalar yo'q", show_alert=True)
        return

    buttons = []
    for poll in polls:
        buttons.append([InlineKeyboardButton(
            text=f"📝 {poll.name}",
            callback_data=f"view_poll_{poll.id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="polls_menu")])

    await callback.message.edit_text(
        "📝 Qoralama so'rovnomalar:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("view_poll_"))
async def view_poll_detail(callback: CallbackQuery):
    """View poll details with management options."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    options = await db.get_poll_options(poll_id)
    total_votes = sum(opt.votes_count for opt in options)

    # Build poll info text
    status_emoji = {"active": "🟢", "finished": "✅", "draft": "📝", "paused": "⏸"}.get(poll.status, "❓")
    text = (
        f"{status_emoji} <b>{poll.name}</b>\n\n"
        f"📊 <b>Status:</b> {poll.status}\n"
        f"👥 <b>Jami ovozlar:</b> {total_votes}\n\n"
        f"<b>Variantlar:</b>\n"
    )

    for opt in options:
        percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "▓" * bar_length + "░" * (10 - bar_length)
        text += f"  • {opt.name}: {opt.votes_count} ({percentage:.1f}%)\n    {bar}\n"

    await callback.message.edit_text(
        text,
        reply_markup=poll_manage_keyboard(poll_id, poll.status, "uz"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pause_poll_"))
async def pause_poll(callback: CallbackQuery):
    """Pause an active poll."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    await db.update_poll(poll_id, status="paused")
    await callback.answer("So'rovnoma to'xtatildi!", show_alert=True)

    # Refresh the view
    poll = await db.get_poll(poll_id)
    options = await db.get_poll_options(poll_id)
    total_votes = sum(opt.votes_count for opt in options)

    status_emoji = {"active": "🟢", "finished": "✅", "draft": "📝", "paused": "⏸"}.get(poll.status, "❓")
    text = (
        f"{status_emoji} <b>{poll.name}</b>\n\n"
        f"📊 <b>Status:</b> {poll.status}\n"
        f"👥 <b>Jami ovozlar:</b> {total_votes}\n\n"
        f"<b>Variantlar:</b>\n"
    )

    for opt in options:
        percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "▓" * bar_length + "░" * (10 - bar_length)
        text += f"  • {opt.name}: {opt.votes_count} ({percentage:.1f}%)\n    {bar}\n"

    await callback.message.edit_text(
        text,
        reply_markup=poll_manage_keyboard(poll_id, poll.status, "uz"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("resume_poll_"))
async def resume_poll(callback: CallbackQuery):
    """Resume a paused poll."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    await db.update_poll(poll_id, status="active")
    await callback.answer("So'rovnoma davom ettirildi!", show_alert=True)

    # Refresh the view
    poll = await db.get_poll(poll_id)
    options = await db.get_poll_options(poll_id)
    total_votes = sum(opt.votes_count for opt in options)

    status_emoji = {"active": "🟢", "finished": "✅", "draft": "📝", "paused": "⏸"}.get(poll.status, "❓")
    text = (
        f"{status_emoji} <b>{poll.name}</b>\n\n"
        f"📊 <b>Status:</b> {poll.status}\n"
        f"👥 <b>Jami ovozlar:</b> {total_votes}\n\n"
        f"<b>Variantlar:</b>\n"
    )

    for opt in options:
        percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "▓" * bar_length + "░" * (10 - bar_length)
        text += f"  • {opt.name}: {opt.votes_count} ({percentage:.1f}%)\n    {bar}\n"

    await callback.message.edit_text(
        text,
        reply_markup=poll_manage_keyboard(poll_id, poll.status, "uz"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("finish_poll_"))
async def finish_poll(callback: CallbackQuery):
    """Finish a poll."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    await db.update_poll(poll_id, status="finished")
    await callback.answer("So'rovnoma tugatildi!", show_alert=True)

    # Refresh the view
    poll = await db.get_poll(poll_id)
    options = await db.get_poll_options(poll_id)
    total_votes = sum(opt.votes_count for opt in options)

    status_emoji = {"active": "🟢", "finished": "✅", "draft": "📝", "paused": "⏸"}.get(poll.status, "❓")
    text = (
        f"{status_emoji} <b>{poll.name}</b>\n\n"
        f"📊 <b>Status:</b> {poll.status}\n"
        f"👥 <b>Jami ovozlar:</b> {total_votes}\n\n"
        f"<b>Variantlar:</b>\n"
    )

    for opt in options:
        percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "▓" * bar_length + "░" * (10 - bar_length)
        text += f"  • {opt.name}: {opt.votes_count} ({percentage:.1f}%)\n    {bar}\n"

    await callback.message.edit_text(
        text,
        reply_markup=poll_manage_keyboard(poll_id, poll.status, "uz"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("publish_poll_"))
async def publish_poll(callback: CallbackQuery, bot: Bot):
    """Publish a draft poll."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    # Get poll options
    options = await db.get_poll_options(poll_id)

    # Build poll message
    text = poll.text

    # Create voting buttons
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(
            text=opt.name,
            callback_data=f"vote_{poll_id}_{opt.id}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        # Send poll to channel
        if poll.media_type == "photo" and poll.media_id:
            msg = await bot.send_photo(
                chat_id=poll.channel_id,
                photo=poll.media_id,
                caption=text,
                reply_markup=keyboard
            )
        elif poll.media_type == "video" and poll.media_id:
            msg = await bot.send_video(
                chat_id=poll.channel_id,
                video=poll.media_id,
                caption=text,
                reply_markup=keyboard
            )
        else:
            msg = await bot.send_message(
                chat_id=poll.channel_id,
                text=text,
                reply_markup=keyboard
            )

        # Update poll status and message_id
        await db.update_poll(poll_id, status="active", message_id=msg.message_id)
        await callback.answer("So'rovnoma kanalga joylandi!", show_alert=True)

    except Exception as e:
        await callback.answer(f"Xatolik: {str(e)}", show_alert=True)
        return

    # Refresh the view
    poll = await db.get_poll(poll_id)
    total_votes = sum(opt.votes_count for opt in options)

    status_emoji = {"active": "🟢", "finished": "✅", "draft": "📝", "paused": "⏸"}.get(poll.status, "❓")
    info_text = (
        f"{status_emoji} <b>{poll.name}</b>\n\n"
        f"📊 <b>Status:</b> {poll.status}\n"
        f"👥 <b>Jami ovozlar:</b> {total_votes}\n\n"
        f"<b>Variantlar:</b>\n"
    )

    for opt in options:
        percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "▓" * bar_length + "░" * (10 - bar_length)
        info_text += f"  • {opt.name}: {opt.votes_count} ({percentage:.1f}%)\n    {bar}\n"

    await callback.message.edit_text(
        info_text,
        reply_markup=poll_manage_keyboard(poll_id, poll.status, "uz"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("delete_poll_"))
async def delete_poll(callback: CallbackQuery):
    """Delete a draft poll."""
    if not await has_permission(callback.from_user.id, "manage_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    if poll.status != "draft":
        await callback.answer("Faqat qoralama so'rovnomalarni o'chirish mumkin!", show_alert=True)
        return

    # Delete poll (you might need to add this method to the database)
    await callback.answer("So'rovnoma o'chirildi!", show_alert=True)
    await callback.message.edit_text(
        f"📊 {get_text('polls', 'uz')}",
        reply_markup=polls_menu_keyboard("uz")
    )


@router.callback_query(F.data == "new_poll")
async def new_poll_start(callback: CallbackQuery, state: FSMContext):
    """Start creating a new poll."""
    if not await has_permission(callback.from_user.id, "create_poll"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    channels = await db.get_poll_channels()
    if not channels:
        await callback.answer("Avval kanal qo'shing!", show_alert=True)
        return

    await callback.message.edit_text(
        get_text("select_channel", "uz"),
        reply_markup=select_channel_keyboard(channels, "uz")
    )
    await state.set_state(AdminPollState.select_channel)


@router.callback_query(F.data.startswith("poll_channel_"), AdminPollState.select_channel)
async def poll_select_channel(callback: CallbackQuery, state: FSMContext):
    """Select channel for poll."""
    channel_id = int(callback.data.split("_")[2])
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(get_text("enter_poll_name", "uz"))
    await state.set_state(AdminPollState.enter_name)


@router.message(AdminPollState.enter_name)
async def poll_enter_name(message: Message, state: FSMContext):
    """Enter poll name."""
    await state.update_data(name=message.text.strip())

    await message.answer(
        get_text("select_content_type", "uz"),
        reply_markup=content_type_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_content_type)


@router.callback_query(F.data.startswith("content_"), AdminPollState.select_content_type)
async def poll_select_content(callback: CallbackQuery, state: FSMContext):
    """Select content type."""
    content_type = callback.data.split("_")[1]
    await state.update_data(media_type=None if content_type == "text" else content_type)

    await callback.message.edit_text(get_text("enter_poll_text", "uz"))
    await state.set_state(AdminPollState.enter_text)


@router.message(AdminPollState.enter_text)
async def poll_enter_text(message: Message, state: FSMContext):
    """Enter poll text."""
    await state.update_data(text=message.text)
    data = await state.get_data()

    if data.get("media_type"):
        await message.answer(get_text("send_media", "uz"))
        await state.set_state(AdminPollState.send_media)
    else:
        await message.answer(get_text("enter_options_count", "uz"))
        await state.set_state(AdminPollState.enter_options_count)


@router.message(AdminPollState.send_media, F.photo | F.video)
async def poll_receive_media(message: Message, state: FSMContext):
    """Receive media for poll."""
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    else:
        media_id = message.video.file_id
        media_type = "video"

    await state.update_data(media_id=media_id, media_type=media_type)
    await message.answer(get_text("enter_options_count", "uz"))
    await state.set_state(AdminPollState.enter_options_count)


@router.message(AdminPollState.enter_options_count)
async def poll_options_count(message: Message, state: FSMContext):
    """Enter number of options."""
    try:
        count = int(message.text)
        if not 2 <= count <= 50:
            raise ValueError
    except ValueError:
        await message.answer("2 dan 50 gacha son kiriting!")
        return

    await state.update_data(options_count=count, options=[], current_option=1)
    await message.answer(get_text("enter_option_name", "uz", n=1))
    await state.set_state(AdminPollState.enter_option_name)


@router.message(AdminPollState.enter_option_name)
async def poll_option_name(message: Message, state: FSMContext):
    """Enter option name."""
    data = await state.get_data()
    options = data.get("options", [])
    current = data.get("current_option", 1)

    options.append({"name": message.text.strip(), "photo_id": None})
    await state.update_data(options=options)

    await message.answer(
        get_text("send_option_photo", "uz", n=current),
        reply_markup=skip_keyboard("uz")
    )
    await state.set_state(AdminPollState.send_option_photo)


@router.callback_query(F.data == "skip", AdminPollState.send_option_photo)
async def poll_skip_photo(callback: CallbackQuery, state: FSMContext):
    """Skip option photo."""
    await process_next_option(callback.message, state)


@router.message(AdminPollState.send_option_photo, F.photo)
async def poll_option_photo(message: Message, state: FSMContext):
    """Receive option photo."""
    data = await state.get_data()
    options = data.get("options", [])
    options[-1]["photo_id"] = message.photo[-1].file_id
    await state.update_data(options=options)
    await process_next_option(message, state)


async def process_next_option(message: Message, state: FSMContext):
    """Process next option or move to layout selection."""
    data = await state.get_data()
    current = data.get("current_option", 1)
    count = data.get("options_count", 2)

    if current < count:
        await state.update_data(current_option=current + 1)
        await message.answer(get_text("enter_option_name", "uz", n=current + 1))
        await state.set_state(AdminPollState.enter_option_name)
    else:
        await message.answer(
            get_text("select_layout", "uz"),
            reply_markup=button_layout_keyboard("uz")
        )
        await state.set_state(AdminPollState.select_layout)


@router.callback_query(F.data.startswith("layout_"), AdminPollState.select_layout)
async def poll_select_layout(callback: CallbackQuery, state: FSMContext):
    """Select button layout."""
    layout = int(callback.data.split("_")[1])
    await state.update_data(button_layout=layout)

    await callback.message.edit_text(
        get_text("select_start_time", "uz"),
        reply_markup=start_time_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_start_time)


@router.callback_query(F.data == "start_now", AdminPollState.select_start_time)
async def poll_start_now(callback: CallbackQuery, state: FSMContext):
    """Start poll now."""
    await state.update_data(scheduled_at=None, status="active")

    await callback.message.edit_text(
        get_text("select_end_condition", "uz"),
        reply_markup=end_condition_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_end_condition)


@router.callback_query(F.data == "schedule_poll", AdminPollState.select_start_time)
async def poll_schedule(callback: CallbackQuery, state: FSMContext):
    """Schedule poll."""
    await callback.message.edit_text(
        get_text("enter_end_date", "uz") + "\n\nMasalan: 2024-12-31 18:00"
    )
    await state.set_state(AdminPollState.enter_schedule_date)


@router.message(AdminPollState.enter_schedule_date)
async def poll_schedule_date(message: Message, state: FSMContext):
    """Enter schedule date."""
    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Noto'g'ri format! YYYY-MM-DD HH:MM formatda kiriting.")
        return

    await state.update_data(scheduled_at=scheduled_at, status="scheduled")

    await message.answer(
        get_text("select_end_condition", "uz"),
        reply_markup=end_condition_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_end_condition)


@router.callback_query(F.data == "end_time", AdminPollState.select_end_condition)
async def poll_end_time(callback: CallbackQuery, state: FSMContext):
    """End at specific time."""
    await callback.message.edit_text(
        get_text("enter_end_date", "uz") + "\n\nMasalan: 2024-12-31 23:59"
    )
    await state.set_state(AdminPollState.enter_end_date)


@router.message(AdminPollState.enter_end_date)
async def poll_end_date(message: Message, state: FSMContext):
    """Enter end date."""
    try:
        ends_at = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Noto'g'ri format!")
        return

    await state.update_data(ends_at=ends_at, end_votes_count=None)

    await message.answer(
        get_text("select_visibility", "uz"),
        reply_markup=results_visibility_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_visibility)


@router.callback_query(F.data == "end_votes", AdminPollState.select_end_condition)
async def poll_end_votes(callback: CallbackQuery, state: FSMContext):
    """End at vote count."""
    await callback.message.edit_text(get_text("enter_end_votes", "uz"))
    await state.set_state(AdminPollState.enter_end_votes)


@router.message(AdminPollState.enter_end_votes)
async def poll_end_votes_count(message: Message, state: FSMContext):
    """Enter end votes count."""
    try:
        count = int(message.text)
        if count < 1:
            raise ValueError
    except ValueError:
        await message.answer("Musbat son kiriting!")
        return

    await state.update_data(end_votes_count=count, ends_at=None)

    await message.answer(
        get_text("select_visibility", "uz"),
        reply_markup=results_visibility_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_visibility)


@router.callback_query(F.data == "end_manual", AdminPollState.select_end_condition)
async def poll_end_manual(callback: CallbackQuery, state: FSMContext):
    """End manually."""
    await state.update_data(ends_at=None, end_votes_count=None)

    await callback.message.edit_text(
        get_text("select_visibility", "uz"),
        reply_markup=results_visibility_keyboard("uz")
    )
    await state.set_state(AdminPollState.select_visibility)


@router.callback_query(F.data.startswith("visibility_"), AdminPollState.select_visibility)
async def poll_visibility(callback: CallbackQuery, state: FSMContext):
    """Select results visibility."""
    visibility_map = {
        "realtime": "realtime",
        "after": "after_finish",
        "admins": "admins_only"
    }
    visibility = visibility_map.get(callback.data.split("_")[1], "realtime")
    await state.update_data(results_visibility=visibility)

    # Show preview
    data = await state.get_data()
    await show_poll_preview(callback.message, data)
    await state.set_state(AdminPollState.preview)


async def show_poll_preview(message: Message, data: dict):
    """Show poll preview."""
    text = f"{get_text('poll_preview', 'uz')}\n\n{data.get('text', '')}"

    # Create fake options for preview
    options = data.get("options", [])
    from app.database.models import PollOption
    preview_options = [
        PollOption(id=i, poll_id=0, name=opt["name"], votes_count=0, position=i)
        for i, opt in enumerate(options)
    ]

    keyboard = poll_options_keyboard(0, preview_options, data.get("button_layout", 1), False)

    if data.get("media_type") == "photo" and data.get("media_id"):
        await message.answer_photo(
            data["media_id"],
            caption=text,
            reply_markup=keyboard
        )
    elif data.get("media_type") == "video" and data.get("media_id"):
        await message.answer_video(
            data["media_id"],
            caption=text,
            reply_markup=keyboard
        )
    else:
        await message.answer(text, reply_markup=keyboard)

    await message.answer(
        "Tasdiqlaysizmi?",
        reply_markup=poll_preview_keyboard("uz")
    )


@router.callback_query(F.data == "confirm_poll", AdminPollState.preview)
async def confirm_poll(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and create poll."""
    data = await state.get_data()

    # Create poll in database
    poll = await db.create_poll(
        channel_id=data["channel_id"],
        name=data["name"],
        text=data["text"],
        created_by=callback.from_user.id,
        media_type=data.get("media_type"),
        media_id=data.get("media_id"),
        button_layout=data.get("button_layout", 1),
        results_visibility=data.get("results_visibility", "realtime"),
        scheduled_at=data.get("scheduled_at"),
        ends_at=data.get("ends_at"),
        end_votes_count=data.get("end_votes_count")
    )

    # Create options
    for i, opt in enumerate(data.get("options", [])):
        await db.create_poll_option(
            poll_id=poll.id,
            name=opt["name"],
            position=i,
            photo_id=opt.get("photo_id")
        )

    # If status is active, publish immediately
    if data.get("status") == "active":
        options = await db.get_poll_options(poll.id)
        keyboard = poll_options_keyboard(poll.id, options, poll.button_layout, False)

        try:
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
            await callback.message.edit_text(get_text("poll_published", "uz"))
        except Exception as e:
            await callback.message.edit_text(f"Xatolik: {e}")
    else:
        await db.update_poll(poll.id, status=data.get("status", "draft"))
        await callback.message.edit_text(get_text("poll_created", "uz"))

    await state.clear()


@router.callback_query(F.data == "cancel_poll")
async def cancel_poll(callback: CallbackQuery, state: FSMContext):
    """Cancel poll creation."""
    await state.clear()
    await callback.message.edit_text(
        f"📊 {get_text('polls', 'uz')}",
        reply_markup=polls_menu_keyboard("uz")
    )


@router.callback_query(F.data == "back_poll_step")
async def back_poll_step(callback: CallbackQuery, state: FSMContext):
    """Go back one step in poll creation."""
    current_state = await state.get_state()
    if current_state is None:
        await callback.message.edit_text(
            f"📊 {get_text('polls', 'uz')}",
            reply_markup=polls_menu_keyboard("uz")
        )
        return

    await callback.answer("Oldingi qadam...")
    # For simplicity, just cancel and start over
    await state.clear()
    await callback.message.edit_text(
        f"📊 {get_text('polls', 'uz')}",
        reply_markup=polls_menu_keyboard("uz")
    )


@router.callback_query(F.data == "edit_poll")
async def edit_poll(callback: CallbackQuery, state: FSMContext):
    """Edit poll before publishing."""
    await callback.answer("Tahrirlash hozircha mavjud emas. So'rovnomani qaytadan yarating.", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Do nothing - for pagination display."""
    await callback.answer()


@router.callback_query(F.data.startswith("export_poll_"))
async def export_poll_report(callback: CallbackQuery):
    """Export poll voting report to Excel."""
    if not await has_permission(callback.from_user.id, "export_data"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    poll_id = int(callback.data.split("_")[-1])
    poll = await db.get_poll(poll_id)

    if not poll:
        await callback.answer("So'rovnoma topilmadi!", show_alert=True)
        return

    await callback.answer("Hisobot tayyorlanmoqda...")

    # Get report data
    votes_data = await db.get_poll_report_data(poll_id)

    if not votes_data:
        await callback.message.answer("Bu so'rovnomada hali ovozlar yo'q.")
        return

    # Create Excel file
    excel_file = create_poll_results_excel(poll.name, votes_data)

    # Send file
    filename = f"hisobot_{poll.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    await callback.message.answer_document(
        BufferedInputFile(excel_file.read(), filename=filename),
        caption=f"📊 So'rovnoma hisoboti: {poll.name}\n"
                f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"👥 Jami ovozlar: {len(votes_data)}"
    )


# ============ USERS MANAGEMENT ============
@router.message(F.text.contains("Foydalanuvchilar") | F.text.contains("Пользователи") | F.text.contains("Users"))
async def users_menu(message: Message):
    """Show users menu."""
    if not await has_permission(message.from_user.id, "view_users"):
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"👥 {get_text('users', 'uz')}",
        reply_markup=users_menu_keyboard("uz")
    )


@router.callback_query(F.data == "users_menu")
async def users_menu_callback(callback: CallbackQuery):
    """Show users menu via callback."""
    await callback.message.edit_text(
        f"👥 {get_text('users', 'uz')}",
        reply_markup=users_menu_keyboard("uz")
    )


@router.callback_query(F.data == "users_list")
async def users_list_callback(callback: CallbackQuery):
    """Show users list."""
    if not await has_permission(callback.from_user.id, "view_users"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    users = await db.get_all_users(limit=20)
    if not users:
        await callback.answer("Foydalanuvchilar yo'q", show_alert=True)
        return

    total = await db.get_users_count()
    text = f"👥 <b>Foydalanuvchilar</b> ({total} ta)\n\n"

    for i, user in enumerate(users, 1):
        status = "🚫" if user.is_blocked else "✅"
        username = f"@{user.username}" if user.username else "-"
        text += f"{i}. {status} {user.full_name} | {username}\n"

    buttons = [[InlineKeyboardButton(text="📥 Excel yuklab olish", callback_data="export_users")]]
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="users_menu")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "search_user")
async def search_user_callback(callback: CallbackQuery, state: FSMContext):
    """Start user search."""
    if not await has_permission(callback.from_user.id, "view_users"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    await callback.message.edit_text(
        "🔍 Foydalanuvchi ID, username yoki telefon raqamini kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="users_menu")]
        ])
    )
    await state.set_state(AdminUserState.search_query)


@router.callback_query(F.data == "blocked_users")
async def blocked_users_callback(callback: CallbackQuery):
    """Show blocked users list."""
    if not await has_permission(callback.from_user.id, "view_users"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    # Get all users and filter blocked ones
    all_users = await db.get_all_users(limit=1000)
    blocked = [u for u in all_users if u.is_blocked]

    if not blocked:
        await callback.answer("Bloklangan foydalanuvchilar yo'q", show_alert=True)
        return

    text = f"🚫 <b>Bloklangan foydalanuvchilar</b> ({len(blocked)} ta)\n\n"

    for i, user in enumerate(blocked[:20], 1):
        username = f"@{user.username}" if user.username else "-"
        text += f"{i}. {user.full_name} | {username}\n"

    buttons = [[InlineKeyboardButton(text="◀️ Orqaga", callback_data="users_menu")]]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "export_users")
async def export_users(callback: CallbackQuery):
    """Export users to Excel."""
    if not await has_permission(callback.from_user.id, "export_data"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    await callback.answer("Tayyorlanmoqda...")

    users = await db.get_all_users(limit=10000)
    users_data = [
        {
            "full_name": u.full_name,
            "phone": u.phone,
            "username": f"@{u.username}" if u.username else "",
            "is_blocked": u.is_blocked,
            "created_at": u.created_at
        }
        for u in users
    ]

    excel_file = create_users_excel(users_data)

    await callback.message.answer_document(
        BufferedInputFile(
            excel_file.read(),
            filename=f"users_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        )
    )


# ============ STATISTICS ============
@router.message(F.text.contains("Statistika") | F.text.contains("Статистика") | F.text.contains("Statistics"))
async def statistics_menu(message: Message):
    """Show statistics menu."""
    if not await has_permission(message.from_user.id, "view_stats"):
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"📈 {get_text('statistics', 'uz')}",
        reply_markup=stats_menu_keyboard("uz")
    )


@router.callback_query(F.data == "general_stats")
async def general_stats(callback: CallbackQuery):
    """Show general statistics."""
    total_users = await db.get_users_count()
    today_users = await db.get_users_count_today()
    week_users = await db.get_users_count_week()
    month_users = await db.get_users_count_month()

    total_polls = await db.get_polls_count()
    active_polls = await db.get_active_polls_count()
    finished_polls = len(await db.get_polls_by_status("finished"))

    total_votes = await db.get_total_votes_count()
    today_votes = await db.get_votes_count_today()
    avg_votes = total_votes // total_polls if total_polls > 0 else 0

    stats_text = get_text("stats_text", "uz",
        total_users=total_users,
        today_users=today_users,
        week_users=week_users,
        month_users=month_users,
        total_polls=total_polls,
        active_polls=active_polls,
        finished_polls=finished_polls,
        total_votes=total_votes,
        today_votes=today_votes,
        avg_votes=avg_votes
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=back_keyboard("uz", "stats_menu")
    )


@router.callback_query(F.data == "daily_stats")
async def daily_stats(callback: CallbackQuery):
    """Show daily statistics."""
    today_users = await db.get_users_count_today()
    today_votes = await db.get_votes_count_today()

    text = (
        f"📊 <b>Kunlik statistika</b>\n\n"
        f"👥 Bugungi foydalanuvchilar: {today_users}\n"
        f"🗳 Bugungi ovozlar: {today_votes}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("uz", "stats_menu"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "weekly_stats")
async def weekly_stats(callback: CallbackQuery):
    """Show weekly statistics."""
    week_users = await db.get_users_count_week()

    text = (
        f"📊 <b>Haftalik statistika</b>\n\n"
        f"👥 Bu haftadagi foydalanuvchilar: {week_users}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("uz", "stats_menu"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "monthly_stats")
async def monthly_stats(callback: CallbackQuery):
    """Show monthly statistics."""
    month_users = await db.get_users_count_month()

    text = (
        f"📊 <b>Oylik statistika</b>\n\n"
        f"👥 Bu oydagi foydalanuvchilar: {month_users}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("uz", "stats_menu"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "stats_menu")
async def stats_menu_callback(callback: CallbackQuery):
    """Back to stats menu."""
    await callback.message.edit_text(
        f"📈 {get_text('statistics', 'uz')}",
        reply_markup=stats_menu_keyboard("uz")
    )


# ============ ADMINS MANAGEMENT ============
@router.message(F.text.contains("Adminlar") | F.text.contains("Админы") | F.text.contains("Admins"))
async def admins_menu(message: Message):
    """Show admins menu."""
    admin = await db.get_admin(message.from_user.id)
    if not admin or not admin.is_super_admin:
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"👨‍💼 {get_text('admins', 'uz')}",
        reply_markup=admins_menu_keyboard("uz")
    )


@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    """Start adding admin."""
    admin = await db.get_admin(callback.from_user.id)
    if not admin or not admin.is_super_admin:
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    await callback.message.edit_text(get_text("enter_admin_id", "uz"))
    await state.set_state(AdminAddAdminState.enter_id)


@router.message(AdminAddAdminState.enter_id)
async def add_admin_id(message: Message, state: FSMContext):
    """Enter admin ID."""
    try:
        admin_id = int(message.text)
    except ValueError:
        await message.answer("Telegram ID son bo'lishi kerak!")
        return

    existing = await db.get_admin(admin_id)
    if existing:
        await message.answer("Bu foydalanuvchi allaqachon admin!")
        await state.clear()
        return

    await state.update_data(admin_id=admin_id, permissions=[])
    await message.answer(
        get_text("select_permissions", "uz"),
        reply_markup=permissions_keyboard([], "uz")
    )
    await state.set_state(AdminAddAdminState.select_permissions)


@router.callback_query(F.data.startswith("perm_"), AdminAddAdminState.select_permissions)
async def toggle_permission(callback: CallbackQuery, state: FSMContext):
    """Toggle permission."""
    perm = callback.data.replace("perm_", "")
    data = await state.get_data()
    perms = data.get("permissions", [])

    if perm in perms:
        perms.remove(perm)
    else:
        perms.append(perm)

    await state.update_data(permissions=perms)
    await callback.message.edit_reply_markup(
        reply_markup=permissions_keyboard(perms, "uz")
    )


@router.callback_query(F.data == "confirm_permissions", AdminAddAdminState.select_permissions)
async def confirm_admin(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and add admin."""
    data = await state.get_data()
    admin_id = data["admin_id"]
    permissions = data.get("permissions", [])

    try:
        user = await bot.get_chat(admin_id)
        await db.create_admin(
            telegram_id=admin_id,
            full_name=user.full_name or str(admin_id),
            username=user.username,
            permissions=permissions,
            added_by=callback.from_user.id
        )
        await callback.message.edit_text(get_text("admin_added", "uz"))
    except Exception as e:
        await callback.message.edit_text(f"Xatolik: {e}")

    await state.clear()


@router.callback_query(F.data == "admin_list")
async def show_admin_list(callback: CallbackQuery):
    """Show list of admins."""
    admins = await db.get_all_admins()

    text = f"👨‍💼 {get_text('admin_list', 'uz')}:\n\n"
    for admin in admins:
        status = "👑" if admin.is_super_admin else "👤"
        text += f"{status} {admin.full_name}"
        if admin.username:
            text += f" (@{admin.username})"
        text += f"\nID: {admin.telegram_id}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("uz", "admins_menu")
    )


@router.callback_query(F.data == "admins_menu")
async def admins_menu_callback(callback: CallbackQuery):
    """Back to admins menu."""
    await callback.message.edit_text(
        f"👨‍💼 {get_text('admins', 'uz')}",
        reply_markup=admins_menu_keyboard("uz")
    )


# ============ SCHEDULED POSTS ============
@router.message(F.text.contains("Postlar") | F.text.contains("Посты") | F.text.contains("Posts"))
async def posts_menu(message: Message):
    """Show posts menu."""
    if not await has_permission(message.from_user.id, "schedule_post"):
        await message.answer(get_text("no_permission", "uz"))
        return

    await message.answer(
        f"📝 {get_text('posts', 'uz')}",
        reply_markup=posts_menu_keyboard("uz")
    )


@router.callback_query(F.data == "posts_menu")
async def posts_menu_callback(callback: CallbackQuery):
    """Show posts menu via callback."""
    await callback.message.edit_text(
        f"📝 {get_text('posts', 'uz')}",
        reply_markup=posts_menu_keyboard("uz")
    )


@router.callback_query(F.data == "new_post")
async def new_post_start(callback: CallbackQuery, state: FSMContext):
    """Start creating a new post."""
    if not await has_permission(callback.from_user.id, "schedule_post"):
        await callback.answer(get_text("no_permission", "uz"), show_alert=True)
        return

    channels = await db.get_all_channels()
    if not channels:
        await callback.answer("Avval kanal qo'shing!", show_alert=True)
        return

    await state.update_data(selected_channels=[])
    await callback.message.edit_text(
        get_text("select_channels", "uz"),
        reply_markup=select_channels_keyboard(channels, [], "uz")
    )
    await state.set_state(AdminPostState.select_channels)


@router.callback_query(F.data.startswith("post_ch_"), AdminPostState.select_channels)
async def post_toggle_channel(callback: CallbackQuery, state: FSMContext):
    """Toggle channel selection for post."""
    channel_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected_channels", [])

    if channel_id in selected:
        selected.remove(channel_id)
    else:
        selected.append(channel_id)

    await state.update_data(selected_channels=selected)

    channels = await db.get_all_channels()
    await callback.message.edit_reply_markup(
        reply_markup=select_channels_keyboard(channels, selected, "uz")
    )


@router.callback_query(F.data == "confirm_channels", AdminPostState.select_channels)
async def post_confirm_channels(callback: CallbackQuery, state: FSMContext):
    """Confirm selected channels."""
    data = await state.get_data()
    selected = data.get("selected_channels", [])

    if not selected:
        await callback.answer("Kamida bitta kanal tanlang!", show_alert=True)
        return

    await callback.message.edit_text(
        "Kontent turini tanlang:",
        reply_markup=post_content_type_keyboard("uz")
    )
    await state.set_state(AdminPostState.enter_text)


@router.callback_query(F.data.startswith("post_content_"), AdminPostState.enter_text)
async def post_select_content_type(callback: CallbackQuery, state: FSMContext):
    """Select content type for post."""
    content_type = callback.data.replace("post_content_", "")

    if content_type == "text":
        await state.update_data(media_type=None)
    else:
        await state.update_data(media_type=content_type)

    await callback.message.edit_text(get_text("enter_post_text", "uz"))


@router.message(AdminPostState.enter_text)
async def post_enter_text(message: Message, state: FSMContext):
    """Enter post text."""
    await state.update_data(text=message.text)
    data = await state.get_data()

    if data.get("media_type"):
        await message.answer(get_text("send_media", "uz"))
        await state.set_state(AdminPostState.send_media)
    else:
        await message.answer(
            "Tugma qo'shishni xohlaysizmi?",
            reply_markup=post_buttons_keyboard("uz")
        )
        await state.set_state(AdminPostState.add_buttons)


@router.message(AdminPostState.send_media, F.photo | F.video | F.document)
async def post_receive_media(message: Message, state: FSMContext):
    """Receive media for post."""
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    else:
        media_id = message.document.file_id
        media_type = "document"

    await state.update_data(media_id=media_id, media_type=media_type)
    await message.answer(
        "Tugma qo'shishni xohlaysizmi?",
        reply_markup=post_buttons_keyboard("uz")
    )
    await state.set_state(AdminPostState.add_buttons)


@router.callback_query(F.data == "add_post_button", AdminPostState.add_buttons)
async def post_add_button(callback: CallbackQuery, state: FSMContext):
    """Add inline button to post."""
    await callback.message.edit_text(
        "Tugma matnini va havolasini yuboring:\n\n"
        "Format: <code>Tugma matni | https://example.com</code>\n\n"
        "Bir nechta tugma uchun har birini yangi qatorda yozing."
    )


@router.message(AdminPostState.add_buttons)
async def post_process_buttons(message: Message, state: FSMContext):
    """Process button input."""
    buttons_data = []
    lines = message.text.strip().split("\n")

    for line in lines:
        if "|" in line:
            parts = line.split("|", 1)
            if len(parts) == 2:
                text = parts[0].strip()
                url = parts[1].strip()
                if text and url:
                    buttons_data.append({"text": text, "url": url})

    if buttons_data:
        await state.update_data(buttons=json.dumps(buttons_data))
    else:
        await state.update_data(buttons=None)

    await message.answer(
        get_text("select_send_time", "uz"),
        reply_markup=post_time_keyboard("uz")
    )
    await state.set_state(AdminPostState.select_time)


@router.callback_query(F.data == "skip_post_buttons", AdminPostState.add_buttons)
async def post_skip_buttons(callback: CallbackQuery, state: FSMContext):
    """Skip adding buttons."""
    await state.update_data(buttons=None)
    await callback.message.edit_text(
        get_text("select_send_time", "uz"),
        reply_markup=post_time_keyboard("uz")
    )
    await state.set_state(AdminPostState.select_time)


@router.callback_query(F.data == "post_send_now", AdminPostState.select_time)
async def post_send_now(callback: CallbackQuery, state: FSMContext):
    """Send post immediately."""
    await state.update_data(scheduled_at=None, send_now=True, repeat_type="once")

    # Show preview
    await show_post_preview(callback.message, state)


@router.callback_query(F.data == "post_schedule", AdminPostState.select_time)
async def post_schedule(callback: CallbackQuery, state: FSMContext):
    """Schedule post."""
    await state.update_data(send_now=False)
    await callback.message.edit_text(
        "Yuborish vaqtini kiriting:\n\nFormat: YYYY-MM-DD HH:MM\nMasalan: 2024-12-31 18:00"
    )
    await state.set_state(AdminPostState.enter_schedule_date)


@router.message(AdminPostState.enter_schedule_date)
async def post_schedule_date(message: Message, state: FSMContext):
    """Enter schedule date."""
    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        if scheduled_at < datetime.now():
            await message.answer("Vaqt o'tib ketgan! Kelajakdagi vaqtni kiriting.")
            return
    except ValueError:
        await message.answer("Noto'g'ri format! YYYY-MM-DD HH:MM formatda kiriting.")
        return

    await state.update_data(scheduled_at=scheduled_at)
    await message.answer(
        get_text("select_repeat", "uz"),
        reply_markup=post_repeat_keyboard("uz")
    )
    await state.set_state(AdminPostState.select_repeat)


@router.callback_query(F.data.startswith("post_repeat_"), AdminPostState.select_repeat)
async def post_select_repeat(callback: CallbackQuery, state: FSMContext):
    """Select repeat type."""
    repeat_type = callback.data.replace("post_repeat_", "")
    await state.update_data(repeat_type=repeat_type)

    # Show preview
    await show_post_preview(callback.message, state)


async def show_post_preview(message: Message, state: FSMContext):
    """Show post preview."""
    data = await state.get_data()

    # Build inline keyboard from buttons
    keyboard = None
    if data.get("buttons"):
        buttons_data = json.loads(data["buttons"])
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], url=btn["url"])]
            for btn in buttons_data
        ])

    text = data.get("text", "")

    # Send preview
    try:
        if data.get("media_type") == "photo" and data.get("media_id"):
            await message.answer_photo(
                data["media_id"],
                caption=text,
                reply_markup=keyboard
            )
        elif data.get("media_type") == "video" and data.get("media_id"):
            await message.answer_video(
                data["media_id"],
                caption=text,
                reply_markup=keyboard
            )
        elif data.get("media_type") == "document" and data.get("media_id"):
            await message.answer_document(
                data["media_id"],
                caption=text,
                reply_markup=keyboard
            )
        else:
            await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        await message.answer(f"Oldindan ko'rishda xatolik: {e}")

    # Show confirmation
    scheduled_info = ""
    if data.get("scheduled_at"):
        scheduled_info = f"\n\n📅 Rejalashtirilgan: {data['scheduled_at'].strftime('%Y-%m-%d %H:%M')}"
        if data.get("repeat_type") != "once":
            repeat_text = {"daily": "Kunlik", "weekly": "Haftalik"}.get(data["repeat_type"], "")
            scheduled_info += f"\n🔄 Takrorlanish: {repeat_text}"
    else:
        scheduled_info = "\n\n▶️ Hozir yuboriladi"

    channels_count = len(data.get("selected_channels", []))
    await message.answer(
        f"📝 Post oldindan ko'rish{scheduled_info}\n\n📢 Kanallar soni: {channels_count}\n\nTasdiqlaysizmi?",
        reply_markup=post_preview_keyboard("uz")
    )
    await state.set_state(AdminPostState.preview)


@router.callback_query(F.data == "confirm_post", AdminPostState.preview)
async def confirm_post(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and send/schedule post."""
    data = await state.get_data()

    channels = data.get("selected_channels", [])
    text = data.get("text", "")
    media_type = data.get("media_type")
    media_id = data.get("media_id")
    buttons = data.get("buttons")
    scheduled_at = data.get("scheduled_at")
    repeat_type = data.get("repeat_type", "once")
    send_now = data.get("send_now", False)

    # Build keyboard
    keyboard = None
    if buttons:
        buttons_data = json.loads(buttons)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], url=btn["url"])]
            for btn in buttons_data
        ])

    if send_now:
        # Send immediately
        success_count = 0
        for channel_id in channels:
            try:
                if media_type == "photo" and media_id:
                    await bot.send_photo(channel_id, media_id, caption=text, reply_markup=keyboard)
                elif media_type == "video" and media_id:
                    await bot.send_video(channel_id, media_id, caption=text, reply_markup=keyboard)
                elif media_type == "document" and media_id:
                    await bot.send_document(channel_id, media_id, caption=text, reply_markup=keyboard)
                else:
                    await bot.send_message(channel_id, text, reply_markup=keyboard)
                success_count += 1
            except Exception as e:
                await callback.message.answer(f"Xatolik (kanal {channel_id}): {e}")

        # Save as sent post
        await db.create_scheduled_post(
            channels=channels,
            text=text,
            created_by=callback.from_user.id,
            media_type=media_type,
            media_id=media_id,
            buttons=buttons,
            scheduled_at=datetime.now(),
            repeat_type="once"
        )
        await db.update_scheduled_post(
            (await db.get_all_scheduled_posts(limit=1))[0].id,
            status="sent"
        )

        await callback.message.edit_text(
            f"✅ Post {success_count}/{len(channels)} kanalga yuborildi!"
        )
    else:
        # Schedule post
        post = await db.create_scheduled_post(
            channels=channels,
            text=text,
            created_by=callback.from_user.id,
            media_type=media_type,
            media_id=media_id,
            buttons=buttons,
            scheduled_at=scheduled_at,
            repeat_type=repeat_type
        )

        await callback.message.edit_text(
            f"✅ Post rejalashtirildi!\n\n"
            f"📅 Vaqti: {scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"📢 Kanallar: {len(channels)} ta"
        )

    await state.clear()


@router.callback_query(F.data == "cancel_post")
async def cancel_post(callback: CallbackQuery, state: FSMContext):
    """Cancel post creation."""
    await state.clear()
    await callback.message.edit_text(
        f"📝 {get_text('posts', 'uz')}",
        reply_markup=posts_menu_keyboard("uz")
    )


@router.callback_query(F.data == "edit_post")
async def edit_post(callback: CallbackQuery, state: FSMContext):
    """Edit post before sending."""
    await callback.answer("Tahrirlash hozircha mavjud emas. Postni qaytadan yarating.", show_alert=True)


@router.callback_query(F.data == "back_post_step")
async def back_post_step(callback: CallbackQuery, state: FSMContext):
    """Go back one step in post creation."""
    await state.clear()
    await callback.message.edit_text(
        f"📝 {get_text('posts', 'uz')}",
        reply_markup=posts_menu_keyboard("uz")
    )


@router.callback_query(F.data == "scheduled_posts")
async def show_scheduled_posts(callback: CallbackQuery):
    """Show list of scheduled posts."""
    posts = await db.get_scheduled_posts_by_status("pending")

    if not posts:
        await callback.answer("Rejalashtirilgan postlar yo'q", show_alert=True)
        return

    await callback.message.edit_text(
        f"📅 {get_text('scheduled_posts', 'uz')}:",
        reply_markup=scheduled_posts_list_keyboard(posts, "uz")
    )


@router.callback_query(F.data == "sent_posts")
async def show_sent_posts(callback: CallbackQuery):
    """Show list of sent posts."""
    posts = await db.get_scheduled_posts_by_status("sent")

    if not posts:
        await callback.answer("Yuborilgan postlar yo'q", show_alert=True)
        return

    text = f"✅ {get_text('sent_posts', 'uz')}:\n\n"
    for i, post in enumerate(posts[:10], 1):
        sent_at = post.scheduled_at.strftime("%d.%m.%Y %H:%M") if post.scheduled_at else "—"
        preview = post.text[:30] + "..." if len(post.text) > 30 else post.text
        text += f"{i}. {sent_at}\n   {preview}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("uz", "posts_menu")
    )


@router.callback_query(F.data.startswith("view_post_"))
async def view_scheduled_post(callback: CallbackQuery):
    """View scheduled post details."""
    post_id = int(callback.data.split("_")[2])
    post = await db.get_scheduled_post(post_id)

    if not post:
        await callback.answer("Post topilmadi", show_alert=True)
        return

    scheduled_at = post.scheduled_at.strftime("%Y-%m-%d %H:%M") if post.scheduled_at else "—"
    repeat_text = {"once": "Bir marta", "daily": "Kunlik", "weekly": "Haftalik"}.get(post.repeat_type, "")

    text = f"📝 Post ma'lumotlari:\n\n"
    text += f"📅 Vaqti: {scheduled_at}\n"
    text += f"🔄 Takrorlanish: {repeat_text}\n"
    text += f"📢 Kanallar: {len(post.channels)} ta\n\n"
    text += f"Matn:\n{post.text[:200]}{'...' if len(post.text) > 200 else ''}"

    await callback.message.edit_text(
        text,
        reply_markup=post_actions_keyboard(post_id, post.status, "uz")
    )


@router.callback_query(F.data.startswith("send_post_now_"))
async def send_scheduled_post_now(callback: CallbackQuery, bot: Bot):
    """Send scheduled post immediately."""
    post_id = int(callback.data.split("_")[3])
    post = await db.get_scheduled_post(post_id)

    if not post:
        await callback.answer("Post topilmadi", show_alert=True)
        return

    # Build keyboard
    keyboard = None
    if post.buttons:
        buttons_data = json.loads(post.buttons)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], url=btn["url"])]
            for btn in buttons_data
        ])

    success_count = 0
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
            success_count += 1
        except Exception as e:
            await callback.message.answer(f"Xatolik: {e}")

    await db.update_scheduled_post(post_id, status="sent")
    await callback.message.edit_text(
        f"✅ Post {success_count}/{len(post.channels)} kanalga yuborildi!"
    )


@router.callback_query(F.data.startswith("delete_post_"))
async def delete_scheduled_post(callback: CallbackQuery):
    """Delete scheduled post."""
    post_id = int(callback.data.split("_")[2])
    await db.delete_scheduled_post(post_id)
    await callback.answer("Post o'chirildi!")

    posts = await db.get_scheduled_posts_by_status("pending")
    if posts:
        await callback.message.edit_text(
            f"📅 {get_text('scheduled_posts', 'uz')}:",
            reply_markup=scheduled_posts_list_keyboard(posts, "uz")
        )
    else:
        await callback.message.edit_text(
            f"📝 {get_text('posts', 'uz')}",
            reply_markup=posts_menu_keyboard("uz")
        )


# ============ BACK BUTTONS ============
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Back to admin main menu."""
    admin = await db.get_admin(callback.from_user.id)
    if admin:
        await callback.message.delete()
        await callback.message.answer(
            get_text("admin_panel", "uz"),
            reply_markup=admin_menu_keyboard("uz", admin.is_super_admin)
        )


@router.callback_query(F.data == "cancel_admin")
async def cancel_admin(callback: CallbackQuery, state: FSMContext):
    """Cancel admin operation."""
    await state.clear()
    await callback.message.edit_text(
        f"👨‍💼 {get_text('admins', 'uz')}",
        reply_markup=admins_menu_keyboard("uz")
    )


# ============ GENERIC HANDLERS ============
@router.callback_query(F.data == "cancel")
async def generic_cancel(callback: CallbackQuery, state: FSMContext):
    """Generic cancel handler - clears state and returns to admin panel."""
    await state.clear()
    admin = await db.get_admin(callback.from_user.id)
    if admin:
        await callback.message.delete()
        await callback.message.answer(
            get_text("admin_panel", "uz"),
            reply_markup=admin_menu_keyboard("uz", admin.is_super_admin)
        )
    else:
        await callback.answer("Bekor qilindi", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass


@router.callback_query(F.data == "confirm")
async def generic_confirm(callback: CallbackQuery, state: FSMContext):
    """Generic confirm handler - just acknowledges."""
    await callback.answer("Tasdiqlandi!", show_alert=True)

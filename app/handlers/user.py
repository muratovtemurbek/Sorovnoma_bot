from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import CommandStart, Command, ChatMemberUpdatedFilter, KICKED, LEFT, RESTRICTED, MEMBER, ADMINISTRATOR, CREATOR
from aiogram.fsm.context import FSMContext
from datetime import datetime

from app.database.database_sqlite import db
from app.states.states import RegistrationState
from app.locales.texts import get_text
from app.keyboards.keyboards import (
    language_keyboard, subscription_keyboard, phone_keyboard,
    main_menu_keyboard, settings_keyboard, back_keyboard,
    poll_options_keyboard
)
from app.utils.antispam import validate_full_name, format_phone_number, calculate_spam_score
from app.utils.captcha import generate_captcha, check_captcha_answer, get_block_until, is_blocked
from app.utils.helpers import check_subscription
from app.config import CAPTCHA_MAX_ATTEMPTS, BLOCK_DURATION_MINUTES

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Handle /start command."""
    user = await db.get_user(message.from_user.id)

    # Check if coming from vote registration link
    start_param = message.text.split(" ", 1)[1] if " " in message.text else None
    from_vote = start_param and (start_param == "register" or start_param.startswith("vote_"))

    # Kanal ID ni olish
    channel_id = None
    if start_param and start_param.startswith("vote_"):
        try:
            channel_id = int(start_param.split("_")[1])
        except (ValueError, IndexError):
            pass

    if user:
        # User already registered
        if user.is_blocked:
            await message.answer(get_text("user_is_blocked", user.language))
            return

        if from_vote and channel_id:
            # Kanalga qaytish tugmasini ko'rsatish
            channel = await db.get_channel(channel_id)
            if channel:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                if channel.username:
                    channel_url = f"https://t.me/{channel.username.lstrip('@')}"
                else:
                    channel_url = f"https://t.me/c/{str(channel_id)[4:]}"

                back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Kanalga qaytish", url=channel_url)]
                ])
                await message.answer(
                    "✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
                    "Endi kanalga qaytib so'rovnomada ovoz berishingiz mumkin.",
                    reply_markup=back_keyboard
                )
            else:
                await message.answer(
                    "✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n"
                    "Endi kanalga qaytib so'rovnomada ovoz berishingiz mumkin.",
                    reply_markup=main_menu_keyboard(user.language)
                )
        else:
            await message.answer(
                get_text("main_menu", user.language),
                reply_markup=main_menu_keyboard(user.language)
            )
        return

    # New user - start registration
    # Kanal ID ni state ga saqlash
    if channel_id:
        await state.update_data(return_channel_id=channel_id)

    if from_vote:
        await message.answer(
            "📝 <b>Ovoz berish uchun ro'yxatdan o'ting!</b>\n\n"
            "Avval tilni tanlang:",
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            get_text("choose_language", "uz"),
            reply_markup=language_keyboard()
        )
    await state.set_state(RegistrationState.language)


@router.callback_query(F.data.startswith("lang_"), RegistrationState.language)
async def process_language(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Process language selection."""
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)

    # Check mandatory subscriptions
    channels = await db.get_mandatory_channels()
    if channels:
        not_subscribed = await check_subscription(bot, callback.from_user.id, channels)
        if not_subscribed:
            await callback.message.edit_text(
                get_text("must_subscribe", lang),
                reply_markup=subscription_keyboard(not_subscribed, lang)
            )
            await state.set_state(RegistrationState.subscription)
            return

    # No mandatory channels or all subscribed
    await callback.message.edit_text(get_text("enter_name", lang))
    await state.set_state(RegistrationState.full_name)


@router.callback_query(F.data == "check_subscription", RegistrationState.subscription)
async def check_sub_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Check subscription status."""
    data = await state.get_data()
    lang = data.get("language", "uz")

    channels = await db.get_mandatory_channels()
    not_subscribed = await check_subscription(bot, callback.from_user.id, channels)

    if not_subscribed:
        await callback.answer(get_text("not_subscribed", lang), show_alert=True)
        await callback.message.edit_reply_markup(
            reply_markup=subscription_keyboard(not_subscribed, lang)
        )
        return

    await callback.answer(get_text("subscription_confirmed", lang))
    await callback.message.edit_text(get_text("enter_name", lang))
    await state.set_state(RegistrationState.full_name)


@router.message(RegistrationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Process full name input."""
    data = await state.get_data()
    lang = data.get("language", "uz")

    if not validate_full_name(message.text):
        await message.answer(get_text("invalid_name", lang))
        return

    await state.update_data(full_name=message.text.strip())
    await message.answer(
        get_text("share_phone", lang),
        reply_markup=phone_keyboard(lang)
    )
    await state.set_state(RegistrationState.phone)


@router.message(RegistrationState.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    """Process phone number from contact."""
    data = await state.get_data()
    lang = data.get("language", "uz")

    phone = format_phone_number(message.contact.phone_number)

    # Check if phone already exists
    if await db.check_phone_exists(phone):
        await message.answer(
            get_text("phone_exists", lang),
            reply_markup=phone_keyboard(lang)
        )
        return

    await state.update_data(phone=phone)

    # Generate captcha
    question, answer = generate_captcha()
    await db.create_captcha(message.from_user.id, answer)

    await message.answer(
        get_text("captcha_prompt", lang, question=question),
        reply_markup=None
    )
    await state.set_state(RegistrationState.captcha)


@router.message(RegistrationState.phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Handle text input when phone is expected."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    await message.answer(
        get_text("share_phone", lang),
        reply_markup=phone_keyboard(lang)
    )


@router.message(RegistrationState.captcha)
async def process_captcha(message: Message, state: FSMContext):
    """Process captcha answer."""
    data = await state.get_data()
    lang = data.get("language", "uz")

    captcha = await db.get_captcha(message.from_user.id)

    if captcha and captcha.blocked_until and is_blocked(captcha.blocked_until):
        await message.answer(
            get_text("captcha_blocked", lang, minutes=BLOCK_DURATION_MINUTES)
        )
        return

    if not captcha:
        question, answer = generate_captcha()
        await db.create_captcha(message.from_user.id, answer)
        await message.answer(get_text("captcha_prompt", lang, question=question))
        return

    if check_captcha_answer(message.text, captcha.correct_answer):
        # Captcha passed - complete registration
        await db.update_captcha_attempts(message.from_user.id, captcha.attempts, is_passed=True)

        # Calculate spam score
        spam_score = calculate_spam_score(message.from_user)

        # Create user
        await db.create_user(
            telegram_id=message.from_user.id,
            full_name=data.get("full_name"),
            username=message.from_user.username,
            phone=data.get("phone"),
            language=lang
        )

        if spam_score > 0:
            await db.update_user(message.from_user.id, spam_score=spam_score)

        # Kanalga qaytish tugmasini tekshirish
        return_channel_id = data.get("return_channel_id")
        await state.clear()

        if return_channel_id:
            # Kanalga qaytish tugmasini ko'rsatish
            channel = await db.get_channel(return_channel_id)
            if channel:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                if channel.username:
                    channel_url = f"https://t.me/{channel.username.lstrip('@')}"
                else:
                    channel_url = f"https://t.me/c/{str(return_channel_id)[4:]}"

                back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Kanalga qaytish va ovoz berish", url=channel_url)]
                ])
                await message.answer(
                    get_text("registration_complete", lang) + "\n\n"
                    "✅ Endi kanalga qaytib so'rovnomada ovoz berishingiz mumkin!",
                    reply_markup=back_keyboard
                )
            else:
                await message.answer(
                    get_text("registration_complete", lang),
                    reply_markup=main_menu_keyboard(lang)
                )
        else:
            await message.answer(
                get_text("registration_complete", lang),
                reply_markup=main_menu_keyboard(lang)
            )
    else:
        # Wrong answer
        attempts = captcha.attempts + 1
        remaining = CAPTCHA_MAX_ATTEMPTS - attempts

        if remaining <= 0:
            # Block user
            blocked_until = get_block_until()
            await db.update_captcha_attempts(
                message.from_user.id, attempts, blocked_until=blocked_until
            )
            await message.answer(
                get_text("captcha_blocked", lang, minutes=BLOCK_DURATION_MINUTES)
            )
        else:
            # Generate new captcha
            question, answer = generate_captcha()
            await db.create_captcha(message.from_user.id, answer)
            await db.update_captcha_attempts(message.from_user.id, attempts)

            await message.answer(
                get_text("captcha_wrong", lang, attempts=remaining) + "\n\n" +
                get_text("captcha_prompt", lang, question=question)
            )


@router.message(Command("menu"))
@router.message(F.text.contains("Asosiy menyu") | F.text.contains("Главное меню") | F.text.contains("Main menu"))
async def cmd_menu(message: Message):
    """Show main menu."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(get_text("must_register", "uz"))
        return

    await message.answer(
        get_text("main_menu", user.language),
        reply_markup=main_menu_keyboard(user.language)
    )


@router.message(F.text.contains("Faol sorovnomalar") | F.text.contains("Активные опросы") | F.text.contains("Active polls"))
async def show_active_polls(message: Message):
    """Show active polls to user."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(get_text("must_register", "uz"))
        return

    polls = await db.get_active_polls()
    if not polls:
        await message.answer(get_text("no_active_polls", user.language))
        return

    for poll in polls:
        options = await db.get_poll_options(poll.id)
        show_results = poll.results_visibility == "realtime"

        text = poll.text
        if show_results:
            total = sum(opt.votes_count for opt in options)
            text += f"\n\n{get_text('total_votes', user.language, count=total)}"

        keyboard = poll_options_keyboard(poll.id, options, poll.button_layout, show_results)

        if poll.media_type == "photo" and poll.media_id:
            await message.answer_photo(poll.media_id, caption=text, reply_markup=keyboard)
        elif poll.media_type == "video" and poll.media_id:
            await message.answer_video(poll.media_id, caption=text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)


@router.message(F.text.contains("Mening ovozlarim") | F.text.contains("Мои голоса") | F.text.contains("My votes"))
async def show_my_votes(message: Message):
    """Show user's voting history."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(get_text("must_register", "uz"))
        return

    # Get user's votes
    votes = await db.get_user_votes_history(message.from_user.id)

    if not votes:
        await message.answer(get_text("no_active_polls", user.language))
        return

    text = f"📈 {get_text('my_votes', user.language)}:\n\n"
    for vote in votes:
        voted_at = vote['voted_at'].strftime("%d.%m.%Y %H:%M") if vote['voted_at'] else ""
        text += f"• {vote['poll_name']}\n  → {vote['option_name']} ({voted_at})\n\n"

    await message.answer(text)


@router.message(F.text.contains("Sozlamalar") | F.text.contains("Настройки") | F.text.contains("Settings"))
async def show_settings(message: Message):
    """Show settings menu."""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(get_text("must_register", "uz"))
        return

    await message.answer(
        f"⚙️ {get_text('settings', user.language)}",
        reply_markup=settings_keyboard(user.language)
    )


@router.callback_query(F.data == "change_language")
async def change_language(callback: CallbackQuery):
    """Show language selection."""
    await callback.message.edit_text(
        get_text("choose_language", "uz"),
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    """Set new language."""
    lang = callback.data.split("_")[1]
    user = await db.get_user(callback.from_user.id)

    if user:
        await db.update_user(callback.from_user.id, language=lang)
        await callback.message.edit_text(get_text("language_set", lang))
        await callback.message.answer(
            get_text("main_menu", lang),
            reply_markup=main_menu_keyboard(lang)
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Go back to main menu."""
    user = await db.get_user(callback.from_user.id)
    if user:
        await callback.message.delete()
        await callback.message.answer(
            get_text("main_menu", user.language),
            reply_markup=main_menu_keyboard(user.language)
        )


@router.message(F.text.contains("Yordam") | F.text.contains("Помощь") | F.text.contains("Help"))
@router.message(Command("help"))
async def show_help(message: Message):
    """Show help message."""
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "uz"
    await message.answer(get_text("help_text", lang))


# Voting handler
@router.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery, bot: Bot):
    """Process user vote."""
    parts = callback.data.split("_")
    poll_id = int(parts[1])
    option_id = int(parts[2])

    # Check if user is registered
    user = await db.get_user(callback.from_user.id)
    if not user:
        # Foydalanuvchi ro'yxatdan o'tmagan - botga yo'naltirish
        bot_info = await bot.get_me()

        # Kanal ma'lumotlarini olish
        poll = await db.get_poll(poll_id)
        channel_id = poll.channel_id if poll else None

        # Start parametriga kanal ID ni qo'shish
        bot_url = f"https://t.me/{bot_info.username}?start=vote_{channel_id}" if channel_id else f"https://t.me/{bot_info.username}?start=register"

        # Foydalanuvchiga shaxsiy xabar yuborishga harakat qilish
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            register_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", url=bot_url)]
            ])
            await bot.send_message(
                callback.from_user.id,
                "⚠️ <b>Ovoz berish uchun ro'yxatdan o'tish kerak!</b>\n\n"
                "So'rovnomada ovoz berish uchun avval botda ro'yxatdan o'ting.\n"
                "Quyidagi tugmani bosing:",
                reply_markup=register_keyboard,
                parse_mode="HTML"
            )
            await callback.answer(
                "📝 Ro'yxatdan o'tish uchun botga o'ting!",
                show_alert=True
            )
        except Exception:
            # Foydalanuvchi botni hali ishga tushirmagan
            await callback.answer(
                f"📝 Ovoz berish uchun avval @{bot_info.username} botida ro'yxatdan o'ting!",
                show_alert=True
            )
        return

    if user.is_blocked:
        await callback.answer(get_text("user_is_blocked", user.language), show_alert=True)
        return

    # Check poll status
    poll = await db.get_poll(poll_id)
    if not poll:
        await callback.answer(get_text("poll_not_found", user.language), show_alert=True)
        return

    if poll.status != "active":
        await callback.answer(get_text("poll_ended", user.language), show_alert=True)
        return

    # Check if already voted
    existing_vote = await db.get_user_vote(poll_id, user.id)
    if existing_vote:
        await callback.answer(get_text("already_voted", user.language), show_alert=True)
        return

    # Create vote
    vote = await db.create_vote(poll_id, option_id, user.id)
    if vote:
        await callback.answer(get_text("vote_accepted", user.language), show_alert=True)

        # Update message with new results
        options = await db.get_poll_options(poll_id)
        show_results = poll.results_visibility == "realtime"

        if show_results:
            text = poll.text
            total = sum(opt.votes_count for opt in options)
            text += f"\n\n{get_text('total_votes', user.language, count=total)}"

            keyboard = poll_options_keyboard(poll_id, options, poll.button_layout, show_results)

            try:
                await callback.message.edit_reply_markup(reply_markup=keyboard)
            except:
                pass

        # Check if poll should end (votes count reached)
        if poll.end_votes_count:
            total_votes = sum(opt.votes_count for opt in options)
            if total_votes >= poll.end_votes_count:
                await db.update_poll(poll_id, status="finished")
    else:
        await callback.answer(get_text("already_voted", user.language), show_alert=True)


# ============ CHANNEL LEAVE DETECTION ============
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(MEMBER | ADMINISTRATOR | CREATOR) >> (LEFT | KICKED)))
async def on_user_left_channel(event: ChatMemberUpdated, bot: Bot):
    """Handle when user leaves or is kicked from channel - cancel their votes."""
    user_id = event.from_user.id
    channel_id = event.chat.id

    # Get user from database
    user = await db.get_user(user_id)
    if not user:
        return

    # Get user's active votes in this channel
    votes = await db.get_user_active_votes_in_channel(user_id, channel_id)

    if not votes:
        return

    cancelled_polls = []

    for vote in votes:
        # Cancel the vote
        success = await db.cancel_vote(vote['vote_id'], vote['option_id'])
        if success:
            cancelled_polls.append(vote['poll_name'])

            # Update poll message in channel to reflect new vote count
            try:
                poll = await db.get_poll(vote['poll_id'])
                if poll and poll.message_id:
                    options = await db.get_poll_options(vote['poll_id'])
                    show_results = poll.results_visibility == "realtime"

                    if show_results:
                        keyboard = poll_options_keyboard(vote['poll_id'], options, poll.button_layout, show_results)
                        await bot.edit_message_reply_markup(
                            chat_id=channel_id,
                            message_id=poll.message_id,
                            reply_markup=keyboard
                        )
            except Exception:
                pass

    # Send notification to user
    if cancelled_polls:
        polls_text = "\n".join([f"• {name}" for name in cancelled_polls])
        message = (
            f"⚠️ <b>Ovozingiz bekor qilindi!</b>\n\n"
            f"Siz kanaldan chiqib ketganingiz sababli quyidagi so'rovnomalardagi ovozlaringiz bekor qilindi:\n\n"
            f"{polls_text}\n\n"
            f"Qayta ovoz berish uchun kanalga obuna bo'ling va so'rovnomada qaytadan ovoz bering."
        )

        try:
            await bot.send_message(user_id, message, parse_mode="HTML")
        except Exception:
            # User may have blocked the bot
            pass

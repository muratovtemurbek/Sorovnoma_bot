from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    language = State()
    subscription = State()
    full_name = State()
    phone = State()
    captcha = State()


class AdminChannelState(StatesGroup):
    waiting_channel = State()
    edit_channel = State()


class AdminPollState(StatesGroup):
    select_channel = State()
    enter_name = State()
    select_content_type = State()
    enter_text = State()
    send_media = State()
    enter_options_count = State()
    enter_option_name = State()
    send_option_photo = State()
    select_layout = State()
    select_start_time = State()
    enter_schedule_date = State()
    select_end_condition = State()
    enter_end_date = State()
    enter_end_votes = State()
    select_visibility = State()
    preview = State()


class AdminPostState(StatesGroup):
    select_channels = State()
    enter_text = State()
    send_media = State()
    select_time = State()
    enter_schedule_date = State()
    select_repeat = State()
    add_buttons = State()
    preview = State()


class AdminUserState(StatesGroup):
    search = State()
    view_user = State()


class AdminAddAdminState(StatesGroup):
    enter_id = State()
    select_permissions = State()

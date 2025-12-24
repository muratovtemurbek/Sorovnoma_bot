# Sorovnoma Bot

Telegram bot for creating and managing polls in channels.

## Features

- Create polls with multiple options
- Support for text, photo, and video polls
- Real-time voting statistics
- Excel report export
- Multi-language support (UZ, RU, EN)
- Admin panel with role-based permissions
- Scheduled posts
- User management
- Anti-spam protection

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/sorovnoma-bot.git
cd sorovnoma-bot
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```

Edit `.env` file:
```
BOT_TOKEN=your_bot_token_here
SUPER_ADMIN_ID=your_telegram_id_here
```

### 5. Run the bot
```bash
python bot.py
```

## Deploy to Railway

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Create new project from GitHub repo
4. Add environment variables:
   - `BOT_TOKEN`
   - `SUPER_ADMIN_ID`

## Project Structure

```
sorovnoma-bot/
├── app/
│   ├── database/       # Database models and operations
│   ├── handlers/       # Message and callback handlers
│   ├── keyboards/      # Inline and reply keyboards
│   ├── locales/        # Translations
│   ├── middlewares/    # Throttling middleware
│   ├── states/         # FSM states
│   └── utils/          # Helper functions
├── bot.py              # Main entry point
├── requirements.txt    # Dependencies
└── Procfile           # Railway deployment
```

## Admin Commands

- `/admin` - Open admin panel
- `/start` - Start the bot

## License

MIT

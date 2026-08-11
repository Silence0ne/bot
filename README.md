# Natiq Bot

A Telegram bot that engages users with daily Quranic content and other Islamic topics.

---

## Project Charter

Project Charter is available in ['Charters'](https://github.com/natiq-foundation/charters/blob/main/charters/bot.md).

---

## Installation & Running

### With Docker (recommended)

```bash
git clone https://github.com/natiq-foundation/bot
cd bot
cp .env.example .env.docker
# edit .env.docker with your settings
# if you want admin access, also set ADMIN_USER_IDS to your numeric Telegram user ID
docker compose up -d --build
```

The bot service will start inside Docker Compose using the values from `.env.docker`.

### Development

You can also run the project without Docker by creating a virtual environment, installing the project and development dependencies, and then starting the bot manually.

For faster local development without Docker:

```bash
uv venv
source .venv/bin/activate
cp .env.example .env.local
uv pip install -r requirements-dev.txt
uv pip install -e .
python -m app
```

### Testing

Execute the test suite with:

```bash
pytest -q
```

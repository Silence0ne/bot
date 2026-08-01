# Natiq Bot

A Telegram bot that engages users with daily Quranic content and other Islamic topics.

---

## Project Charter

Project Charter is available in ['bot.md`](https://github.com/natiq-foundation/charters/blob/main/charters/bot.md).

---

## Installation & Running

### With Docker (recommended)

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
cp .env.example .env.docker
# edit .env.docker with your settings
# if you want admin access, also set ADMIN_USER_IDS to your numeric Telegram user ID
docker compose up -d --build
```

The bot service will start inside Docker Compose using the values from `.env.docker`.

### Other methods

You can also run the project without Docker by creating a virtual environment, installing the project and development dependencies, and then starting the bot manually.

### Development

For faster local development without Docker:

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install -e .
python -m app
```

### Testing

Execute the test suite with:

```bash
pytest -q
```

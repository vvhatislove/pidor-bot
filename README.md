# 🤖 PidorBot

**PidorBot** — Telegram-бот, написанный на Python, использующий `aiogram`, `SQLAlchemy`, OpenRouter и внутриигровую
механику. Бот выбирает "пидора дня", управляет дуэлями между участниками, внутренней валютой и взаимодействует с OpenRouter
для генерации фраз и ответов.

## 📦 Стек технологий

- Python 3.12.9
- [aiogram](https://docs.aiogram.dev/) — фреймворк для Telegram-ботов
- [SQLAlchemy](https://www.sqlalchemy.org/) + [aiosqlite](https://aiosqlite.omnilib.dev/) — асинхронная ORM и SQLite
- [alembic](https://alembic.sqlalchemy.org/) — миграции БД
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — конфигурация через `.env`
- [OpenRouter](https://openrouter.ai/) — генерация фраз и ответов через OpenAI-совместимый API
- `requests` — для внешних HTTP-запросов


## 📋 Переменные окружения (.env)
```env
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=telegram_id_админа
DATABASE_URL=sqlite+aiosqlite:///./pidorbot.db
BOT_NAME=PidorBot
OPENROUTER_API_KEY=ваш_ключ_OpenRouter
TIMEZONE=Europe/Kyiv # или другой часовой пояс

# LLM через OpenRouter
# AI_MODEL=mistralai/mistral-small-3.2-24b-instruct  # дефолт см. config/constants.LLMDefaults; дешевле: qwen/qwen-2.5-7b-instruct
# OPENROUTER_CHAT_MODEL=mistralai/mistral-small-3.2-24b-instruct  # legacy alias; лучше использовать AI_MODEL
# OPENROUTER_HTTP_REFERER=https://github.com/you/pidor-bot  # опционально, для OpenRouter

# Буфер готовых ответов для AI-промптов без контекста (не применяется к триггерам)
# AI_BUFFER_TARGET_SIZE=10
# AI_BUFFER_REFILL_INTERVAL_SECONDS=30
# AI_BUFFER_GENERATION_CONCURRENCY=2
# AI_BUFFER_STORAGE_PATH=database/storage/ai_response_buffer.json
```

## ⚙️ Установка и запуск

# 1. Клонируем репозиторий
```bash
git clone https://github.com/vvhatislove/pidor-bot
cd pidor-bot
````

# 2. Создаём и активируем виртуальное окружение
```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

# 3. Устанавливаем зависимости
```bash
pip install -e .
```

# 4. Применяем миграции
```bash
alembic upgrade head
```

# 5. Запускаем бота
```bash
python main.py
```

## ⚙️ Установка и запуск через Docker


# 1. Собираем образ
```bash
docker build -t pidorbot 
```
# 2. Запускаем контейнер
```bash
docker compose up -d
```

## 💬 Команды бота
Пользовательские команды:
- `pidor` - 🤡 Определить пидора дня
- `auto_pidor` - 🔄 Автоопределение пидора каждый день
- `slots` - 🎰 Крутнуть пидор-казино
- `reg` - 📝 Регистрация на игру
- `unreg` - ❌ Отменить регистрацию
- `stats` - 📊 Статистика чата
- `profile` - 👤 Профиль пользователя
- `achievements` - 🏅 Мои достижения
- `updatedata` - ♻️ Обновить данные в ПидорБазе
- `duel` - ⚔️ Вызвать на дуэль: /duel @username сумма
- `balance` - 💰 Узнать баланс
- `help` - 📖 Помощь по командам

Админские команды:
- `sendglobalmessage <текст>` - Глобальное сообщение

## 🧠 Возможности

- Интерактивные дуэли между участниками
- Игровая валюта и система ставок
- Генерация текстов и фраз с помощью OpenRouter
- Гибкая система команд и расширяемая архитектура

## 🧬 Миграции Alembic

Создание новой миграции:

```bash
alembic revision --autogenerate -m "описание изменений"
```

Применение:

```bash
alembic upgrade head
```

## 🛠 Зависимости

Все зависимости перечислены в `pyproject.toml`.

## 📄 Лицензия

[GPL 3.0](./LICENSE)

---

**Автор:** [vvhatislove](https://github.com/vvhatislove)

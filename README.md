# 🤖 PidorBot

**PidorBot** — Telegram-бот, написанный на Python, использующий `aiogram`, `SQLAlchemy`, `OpenAI` и внутриигровую
механику. Бот выбирает "пидора дня", управляет дуэлями между участниками, внутренней валютой и взаимодействует с OpenAI
для генерации фраз и ответов.

## 📦 Стек технологий

- Python 3.12.9
- [aiogram](https://docs.aiogram.dev/) — фреймворк для Telegram-ботов
- [SQLAlchemy](https://www.sqlalchemy.org/) + [aiosqlite](https://aiosqlite.omnilib.dev/) — асинхронная ORM и SQLite
- [alembic](https://alembic.sqlalchemy.org/) — миграции БД
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — конфигурация через `.env`
- [OpenAI API](https://platform.openai.com/docs/) — генерация фраз, ответов
- `requests` — для внешних HTTP-запросов

## ⚙️ Установка и запуск

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourusername/pidorbot.git
cd pidorbot

# 2. Создаём и активируем виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Устанавливаем зависимости
pip install -r requirements.txt

# 4. Создаём .env файл и указываем переменные окружения
cp .env.example .env
# Редактируем .env:
# BOT_TOKEN=...
# ADMIN_ID=...
# DATABASE_URL=sqlite+aiosqlite:///./pidorbot.db
# BOT_NAME=PidorBot
# OPENAI_API_KEY=...

# 5. Применяем миграции
alembic upgrade head

# 6. Запускаем бота
python main.py
```

## 📋 Переменные окружения (.env)

```env
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=telegram_id_админа
DATABASE_URL=sqlite+aiosqlite:///./pidorbot.db
BOT_NAME=PidorBot
OPENAI_API_KEY=ваш_ключ_OpenAI
```

## 💬 Команды бота

- `/pidor` - 🤡 Определить пидора дня
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

## 🧠 Возможности

- Интерактивные дуэли между участниками
- Игровая валюта и система ставок
- Генерация текстов и фраз с помощью OpenAI
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

Все зависимости перечислены в `requirements.txt`.

## 📄 Лицензия

GPL 3.0

---

**Автор:** [vvhatislove]
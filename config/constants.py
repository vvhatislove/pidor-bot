from enum import Enum
from typing import List, Dict, Tuple


class CommandText(str, Enum):
    """Тексты команд для разных контекстов"""
    START = (
        "Приветствую {name}👋. Я Пидор Бот🌈, чтобы воспользоваться мною, "
        "добавь меня в чат к своим друзьям или коллегам💪"
    )
    START_PRIVATE = (
        "Приветствую {name}👋. Я Пидор Бот🌈, чтобы воспользоваться мною, добавь меня в чат к своим друзьям или коллегам💪, и пропиши там 👉/start@pidorochek_bot"
    )
    START_GROUP = (
        "Приветствую обитателей чата {chat_title}👋.\nЯ Пидор Бот🌈, вот вам краткая инструкция:\n"
        "1. Все участники должны написать /reg\n"
        "2. После регистрации используйте /pidor\n"
        "3. Для помощи - /help"
    )
    ERROR = "В моем Пидор механизме какой-то сбой⌛. Попробуй еще раз♻"
    WRONG_CHAT = "Ты долбаеб👺, в группу меня кинь и там прописывай эту команду☝"


class Commands:
    """Списки команд для разных пользователей"""
    PUBLIC_GROUP = [
        ("/pidor", "Определить пидора дня"),
        ("/reg", "Регистрация на игру"),
        ("/unreg", "Отменить регистрацию"),
        ("/stats", "Статистика чата"),
        ("/achievements", "Мои достижения")
    ]

    PRIVATE = [
        ("/start", "Начало работы"),
        ("/help", "Помощь")
    ]

    ADMIN = [
        ("/changecooldowntime <секунды>", "Изменить кулдаун для всех чатов"),
        ("/sendglobalmessage <текст>", "Глобальное сообщение")
    ]


class GameText:
    """Тексты для игровой механики"""
    TRIGGERS: List[str] = [
        "pidr", "pidor", "пидор", "пидр",
        "педик", "гей", "faggot", "гомосятина"
    ]

    ANSWERS: List[str] = [
        "+", "Я в деле🤝", "Это по мне)🥷",
        "Мёд для моих ушей🍯", "О да!😈"
    ]

    WIN_PHRASES: List[str] = [
        "🙀На сегодня пидорас {winner}",
        "👺Думал спрячешься??? А вот и нет, встречайте пидораса {winner}",
        "☝️Ни что так не бодрит с утра как палец в очке у пидораса {winner}"
    ]

    SEARCH_PHRASES: List[str] = [
        "🗺Смотрю на карту пидорасов",
        "🍵Гадаю на кофейной сперме",
        "📈Определяю кривизну ануса по Гауссу"
    ]

    ACHIEVEMENTS: Dict[int, Tuple[str, str]] = {
        1: ("🍍 Твоя первая анальная пробка", "Стать пидором 1 раз"),
        3: ("🍩 Добро пожаловать в Анал-Лэнд", "Стать пидором 3 раза"),
        10: ("🧘🏿 Открой в себе Gachi-чакру", "Стать пидором 10 раз"),
        100: ("🔥 Путь к гейскому мастерству", "Стать пидором 100 раз")
    }


class HTTPConfig:
    """Настройки HTTP-запросов"""
    HEADERS: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    }
    DAMN_URL: str = "https://damn.ru/?name={name}&sex={sex}"


class Cooldown:
    """Настройки кулдаунов"""
    DEFAULT: int = 86400  # 24 часа в секундах
    MESSAGES: Dict[str, str] = {
        'hours': "До следующего определения пидора🌈 осталось {time} {form}⏳",
        'minutes': "До следующего определения пидора🌈 осталось {time} минут(ы)⏳"
    }
"""
Инлайн-клавиатуры бота.
"""

from collections.abc import Sequence

from telebot import types

# Человекочитаемые подписи кнопок главного меню.
BTN_TRAINING = "📚 Тренировка"
BTN_STATS = "📊 Статистика"
BTN_LEADERBOARD = "🏆 Таблица лидеров"
BTN_MENU = "🏠 В меню"


def get_main_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню бота."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text=BTN_TRAINING, callback_data="training_start"))
    keyboard.row(
        types.InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        types.InlineKeyboardButton(text=BTN_LEADERBOARD, callback_data="leaderboard"),
    )
    return keyboard


def get_back_to_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Одна кнопка возврата в меню."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard


def get_leaderboard_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопки под таблицей лидеров."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="🔄 Обновить", callback_data="leaderboard"))
    keyboard.row(types.InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard


def get_answer_keyboard(question_id: int, attempt: int,
                        options: Sequence[str]) -> types.InlineKeyboardMarkup:
    """
    Кнопки вариантов ответа.

    callback_data = a:<id задания>:<поколение клавиатуры>:<индекс варианта>.
    После неверного ответа поколение растёт, поэтому клики по старым кнопкам
    отбрасываются — это защищает от перебора вариантов.
    Индекс вместо слова гарантированно укладывается в лимит Telegram (64 байта).
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for idx, option in enumerate(options):
        keyboard.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"a:{question_id}:{attempt}:{idx}",
        ))
    keyboard.add(types.InlineKeyboardButton(text=BTN_MENU, callback_data="main_menu"))
    return keyboard

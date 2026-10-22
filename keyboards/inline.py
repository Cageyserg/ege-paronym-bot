"""
Модуль для создания инлайн-клавиатур бота.
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard():
    """Создаёт главное меню бота."""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(text="📚 Тренировка", callback_data="training_start")
    )
    keyboard.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="leaderboard")
    )
    return keyboard


def get_training_answer_keyboard(words):
    """Создаёт клавиатуру с вариантами ответов для тренировки."""
    keyboard = InlineKeyboardMarkup()
    for word in words:
        keyboard.row(InlineKeyboardButton(text=word, callback_data=f"answer_{word}"))
    
    keyboard.row(InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    
    return keyboard


def get_back_to_menu_keyboard():
    """Создаёт клавиатуру с кнопкой возврата в меню."""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard


def get_dictionary_navigation_keyboard(current_index, total):
    """Создаёт клавиатуру навигации по словарю."""
    keyboard = InlineKeyboardMarkup()
    
    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"dict_prev_{current_index}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current_index + 1}/{total}", callback_data="dict_info"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"dict_next_{current_index}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    keyboard.row(InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"))
    
    return keyboard


def get_leaderboard_keyboard():
    """Создаёт клавиатуру для таблицы лидеров."""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton(text="Обновить", callback_data="leaderboard"))
    keyboard.row(InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard

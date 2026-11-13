"""
Модуль для создания инлайн-клавиатур бота.
"""

from telebot import types


def get_main_menu_keyboard():
    """Создаёт главное меню бота."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(text="📚 Тренировка", callback_data="training_start")
    )
    keyboard.row(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        types.InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="leaderboard")
    )
    return keyboard


def get_back_to_menu_keyboard():
    """Создаёт клавиатуру с кнопкой возврата в меню."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard


def get_dictionary_navigation_keyboard(current_index, total):
    """Создаёт клавиатуру навигации по словарю."""
    keyboard = types.InlineKeyboardMarkup()
    
    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"dict_prev_{current_index}"))
    nav_buttons.append(types.InlineKeyboardButton(text=f"{current_index + 1}/{total}", callback_data="dict_info"))
    if current_index < total - 1:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"dict_next_{current_index}"))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    keyboard.row(types.InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"))
    
    return keyboard


def get_leaderboard_keyboard():
    """Создаёт клавиатуру для таблицы лидеров."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="Обновить", callback_data="leaderboard"))
    keyboard.row(types.InlineKeyboardButton(text="В меню", callback_data="main_menu"))
    return keyboard


def get_answer_keyboard(question_id: int, attempt: int, options: list):
    """callback_data несёт id задания, поколение клавиатуры и индекс варианта.
    После неверного ответа поколение растёт — клики по старым кнопкам мертвы.
    Индекс вместо слова: гарантированно влезает в лимит Telegram 64 байта."""
    kb = types.InlineKeyboardMarkup(row_width=1)
    for idx, option in enumerate(options):
        kb.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"a:{question_id}:{attempt}:{idx}"
        ))
    kb.add(types.InlineKeyboardButton("🏠 В меню", callback_data="main_menu"))
    return kb

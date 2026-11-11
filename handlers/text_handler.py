"""
Обработчик текстовых сообщений для тренировки.
Использует глобальный data_manager из utils.data_manager.
"""

import logging
from keyboards.inline import get_main_menu_keyboard
# Глобальный data_manager (инициализируется в main.py)
from utils.data_manager import data_manager

logger = logging.getLogger(__name__)

# Хранилище текущих вопросов пользователей (chat_id -> question_dict)
current_questions = {}


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение - не используется, ответы через кнопки."""
    bot.send_message(
        message.chat.id,
        "Пожалуйста, используйте кнопки для выбора ответа.",
        reply_markup=get_main_menu_keyboard()
    )


def set_current_questions(questions_dict):
    """Устанавливает словарь текущих вопросов."""
    global current_questions
    current_questions = questions_dict

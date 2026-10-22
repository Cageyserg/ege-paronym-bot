"""
Обработчик текстовых сообщений для тренировки.
"""

import logging
from keyboards.inline import get_main_menu_keyboard
from utils.data_manager import DataManager

data_manager = DataManager()
logger = logging.getLogger(__name__)


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение."""
    # Если не в тренировке, просто возвращаем в меню
    bot.send_message(
        message.chat.id,
        "Введите /start для начала работы с ботом",
        reply_markup=get_main_menu_keyboard()
    )

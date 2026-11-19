"""
Обработчик текстовых сообщений.

Ответы принимаются только кнопками, поэтому любой текст вне команд вежливо
возвращает пользователя в меню.
"""

import logging

from keyboards.inline import get_main_menu_keyboard

logger = logging.getLogger(__name__)

HINT_TEXT = "Пожалуйста, используйте кнопки для выбора ответа."


def handle_text_check(message, bot):
    """Подсказывает пользователю отвечать кнопками."""
    bot.send_message(
        message.chat.id,
        HINT_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

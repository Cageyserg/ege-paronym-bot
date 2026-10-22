"""
Обработчик команды /start.
"""

import logging
from keyboards.inline import get_main_menu_keyboard

logger = logging.getLogger(__name__)


def cmd_start(message, bot):
    """Обрабатывает команду /start и показывает главное меню."""
    try:
        logger.info(f"Получена команда /start от user_id={message.from_user.id}")
        bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать в бота для подготовки к ЕГЭ!\n\n"
            "Этот бот поможет вам освоить паронимы и лексические нормы (Задание 5).\n\n"
            "Выберите режим работы:",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Сообщение отправлено в chat_id={message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)

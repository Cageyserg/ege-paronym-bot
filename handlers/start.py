"""
Обработчик команды /start.
"""

from keyboards.inline import get_main_menu_keyboard


def cmd_start(message, bot):
    """Обрабатывает команду /start и показывает главное меню."""
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в бота для подготовки к ЕГЭ!\n\n"
        "Этот бот поможет вам освоить паронимы и лексические нормы (Задание 5).\n\n"
        "Выберите режим работы:",
        reply_markup=get_main_menu_keyboard()
    )

"""
Обработчик текстовых сообщений для проверки текста.
"""

from keyboards.inline import get_main_menu_keyboard
from utils.data_manager import DataManager

data_manager = DataManager()


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение для проверки паронимов."""
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем, есть ли в тексте паронимы
    paronym_info = data_manager.find_paronym_in_text(text)
    
    if paronym_info:
        words = paronym_info["words"]
        definitions = paronym_info["definitions"]
        examples = paronym_info["examples"]
        
        response = (
            f"🔍 Найдены паронимы в вашем тексте!\n\n"
            f"Пара: {words[0]} — {words[1]}\n\n"
            f"Значения:\n"
            f"• {words[0]}: {definitions[words[0]]}\n"
            f"• {words[1]}: {definitions[words[1]]}\n\n"
            f"Примеры:\n"
            f"• {words[0]}: {examples[words[0]]}\n"
            f"• {words[1]}: {examples[words[1]]}\n\n"
            f"💡 Подсказка: обратите внимание на контекст, чтобы выбрать правильное слово."
        )
    else:
        response = (
            f"🔍 В вашем тексте не найдены известные паронимы.\n\n"
            f"Текст: {text}\n\n"
            f"Попробуйте использовать слова из базы паронимов бота."
        )
    
    bot.send_message(
        message.chat.id,
        response,
        reply_markup=get_main_menu_keyboard()
    )

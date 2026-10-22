"""
Обработчик текстовых сообщений для проверки текста и тренировки.
"""

import logging
from keyboards.inline import get_main_menu_keyboard, get_back_to_menu_keyboard
from utils.data_manager import DataManager
from handlers.callbacks import current_questions, user_states

data_manager = DataManager()
logger = logging.getLogger(__name__)


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение."""
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем, находится ли пользователь в режиме тренировки
    if user_states.get(user_id) == "waiting_for_answer":
        handle_training_answer(message, bot)
        return
    
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


def handle_training_answer(message, bot):
    """Обрабатывает ответ пользователя в режиме тренировки."""
    user_id = message.from_user.id
    username = message.from_user.username
    answer = message.text.strip()
    
    logger.info(f"Получен ответ от user_id={user_id}: {answer}")
    
    if user_id not in current_questions:
        bot.send_message(
            message.chat.id,
            "❌ Вопрос не найден. Начните тренировку заново.",
            reply_markup=get_main_menu_keyboard()
        )
        user_states[user_id] = None
        return
    
    question = current_questions[user_id]
    is_correct = answer.lower() == question['correct'].lower()
    
    # Сбрасываем состояние
    user_states[user_id] = None
    
    # Обновляем статистику
    paronym_id = question.get('paronym_id')
    word = question.get('correct') if is_correct else None
    data_manager.update_user_stats(user_id, is_correct, username, paronym_id, word)
    
    if is_correct:
        solved_count = data_manager.get_user_solved_words_count(user_id)
        response_text = (
            f"✅ Правильно!\n\n"
            f"Ваш ответ: {answer}\n"
            f"{question['explanation']}\n\n"
            f"📚 Вы освоили {solved_count} слов!"
        )
    else:
        response_text = (
            f"❌ Неправильно!\n\n"
            f"Ваш ответ: {answer}\n"
            f"Правильный ответ: {question['correct']}\n\n"
            f"{question['explanation']}\n\n"
            f"Значения слов:\n"
            f"• {question['words'][0]}: {question['definitions'][question['words'][0]]}\n"
            f"• {question['words'][1]}: {question['definitions'][question['words'][1]]}"
        )
    
    bot.send_message(
        message.chat.id,
        response_text,
        reply_markup=get_back_to_menu_keyboard()
    )

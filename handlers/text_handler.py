"""
Обработчик текстовых сообщений для тренировки.
"""

import logging
from keyboards.inline import get_main_menu_keyboard, get_back_to_menu_keyboard
from utils.data_manager import DataManager
from handlers.callbacks import current_questions, user_states

data_manager = DataManager()
logger = logging.getLogger(__name__)


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение."""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем, находится ли пользователь в режиме тренировки
    if user_states.get(user_id) == "waiting_for_answer":
        handle_training_answer(message, bot)
        return
    
    # Если не в тренировке, просто возвращаем в меню
    bot.send_message(
        message.chat.id,
        "❓ Введите /start для начала работы с ботом",
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
    
    # Редактируем предыдущее сообщение с результатом
    try:
        bot.edit_message_text(
            message.chat.id,
            message.message_id,
            response_text,
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        # Если редактирование не удалось, отправляем новое сообщение
        bot.send_message(
            message.chat.id,
            response_text,
            reply_markup=get_back_to_menu_keyboard()
        )
    
    # Получаем новый вопрос
    new_question = data_manager.get_random_question()
    
    if new_question:
        # Сохраняем новый вопрос
        current_questions[user_id] = new_question
        # Устанавливаем состояние ожидания ответа
        user_states[user_id] = "waiting_for_answer"
        
        # Отправляем новое сообщение с новым вопросом
        bot.send_message(
            message.chat.id,
            f"📚 Следующий вопрос\n\n"
            f"Вставьте правильное слово:\n\n"
            f"{new_question['sentence']}\n\n"
            f"💡 Варианты: {', '.join(new_question['words'])}\n\n"
            f"📝 Введите слово:",
            reply_markup=get_back_to_menu_keyboard()
        )
    else:
        # Если нет больше вопросов
        user_states[user_id] = None
        bot.send_message(
            message.chat.id,
            "🎉 Вы прошли все доступные вопросы!",
            reply_markup=get_main_menu_keyboard()
        )

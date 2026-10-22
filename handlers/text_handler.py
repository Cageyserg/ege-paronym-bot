"""
Обработчик текстовых сообщений для тренировки.
"""

import logging
from keyboards.inline import get_main_menu_keyboard, get_back_to_menu_keyboard
from utils.data_manager import DataManager

data_manager = DataManager()
logger = logging.getLogger(__name__)

# Хранилище текущих вопросов пользователей (импортируем из callbacks)
current_questions = {}


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение - проверяет ответ пользователя."""
    user_id = message.from_user.id
    username = message.from_user.username
    user_answer = message.text.strip().upper()
    
    # Проверяем, есть ли у пользователя активный вопрос
    if user_id not in current_questions:
        bot.send_message(
            message.chat.id,
            "Начните тренировку, нажав на кнопку «Тренировка» в меню",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    question = current_questions[user_id]
    correct_answer = question['correct_answer'].upper()
    
    # Проверяем ответ
    is_correct = user_answer == correct_answer
    
    # Обновляем статистику
    data_manager.update_user_stats(user_id, is_correct, username, question['id'], correct_answer if is_correct else None)
    
    if is_correct:
        response_text = (
            f"✅ Правильно!\n\n"
            f"Ответ: {question['correct_answer']}\n"
            f"{question['explanation']}"
        )
    else:
        response_text = (
            f"❌ Неправильно!\n\n"
            f"Ваш ответ: {message.text}\n"
            f"Правильный ответ: {question['correct_answer']}\n\n"
            f"{question['explanation']}"
        )
    
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
        
        # Формируем текст с 5 предложениями
        sentences_text = ""
        for i, sentence in enumerate(new_question['sentences'], 1):
            sentences_text += f"{i}. {sentence}\n"
        
        # Отправляем новое сообщение с новым вопросом
        bot.send_message(
            message.chat.id,
            f"📝 Задание 5 ЕГЭ\n\n"
            f"В одном из предложений НЕВЕРНО употреблено выделенное слово.\n"
            f"Исправьте ошибку и напишите правильное слово.\n\n"
            f"{sentences_text}\n"
            f"💡 Напишите правильное слово в чат",
            reply_markup=get_back_to_menu_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "🎉 Вы прошли все доступные вопросы!",
            reply_markup=get_main_menu_keyboard()
        )


def set_current_questions(questions_dict):
    """Устанавливает словарь текущих вопросов."""
    global current_questions
    current_questions = questions_dict

"""
Обработчики callback-запросов (нажатия на инлайн-кнопки).
"""

from keyboards.inline import (
    get_main_menu_keyboard,
    get_training_answer_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard
)
from utils.data_manager import DataManager

data_manager = DataManager()

# Хранилище текущих вопросов пользователей
current_questions = {}


def show_main_menu(call, bot):
    """Показывает главное меню."""
    bot.edit_message_text(
        "Главное меню\n\nВыберите режим работы:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_main_menu_keyboard()
    )


def start_training(call, bot):
    """Начинает режим тренировки."""
    user_id = call.from_user.id
    username = call.from_user.username
    question = data_manager.get_random_question()
    
    if not question:
        bot.answer_callback_query(call.id, "Нет доступных вопросов!", show_alert=True)
        return
    
    # Сохраняем текущий вопрос для пользователя
    current_questions[user_id] = question
    
    bot.edit_message_text(
        f"Тренировка\n\n"
        f"Вставьте правильное слово:\n\n"
        f"{question['sentence']}\n\n"
        f"Варианты: {', '.join(question['words'])}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_training_answer_keyboard(question['words'])
    )


def handle_answer(call, bot):
    """Обрабатывает ответ пользователя на вопрос."""
    user_id = call.from_user.id
    username = call.from_user.username
    answer = call.data.split("_", 1)[1]
    
    if user_id not in current_questions:
        bot.answer_callback_query(call.id, "Вопрос не найден. Начните тренировку заново.", show_alert=True)
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
            f"Правильно!\n\n"
            f"Ответ: {question['correct']}\n"
            f"{question['explanation']}\n\n"
            f"Вы освоили {solved_count} слов!"
        )
    else:
        response_text = (
            f"Неправильно!\n\n"
            f"Ваш ответ: {answer}\n"
            f"Правильный ответ: {question['correct']}\n\n"
            f"{question['explanation']}\n\n"
            f"Значения слов:\n"
            f"• {question['words'][0]}: {question['definitions'][question['words'][0]]}\n"
            f"• {question['words'][1]}: {question['definitions'][question['words'][1]]}"
        )
    
    bot.edit_message_text(
        response_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )
    
    # Получаем новый вопрос
    new_question = data_manager.get_random_question()
    
    if new_question:
        # Сохраняем новый вопрос
        current_questions[user_id] = new_question
        
        # Отправляем новое сообщение с новым вопросом
        bot.send_message(
            call.message.chat.id,
            f"Следующий вопрос\n\n"
            f"Вставьте правильное слово:\n\n"
            f"{new_question['sentence']}",
            reply_markup=get_training_answer_keyboard(new_question['words'])
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "Вы прошли все доступные вопросы!",
            reply_markup=get_main_menu_keyboard()
        )


def next_question(call, bot):
    """Показывает следующий вопрос."""
    # Для текстового ввода next_question больше не нужен
    bot.answer_callback_query(call.id, "Начните тренировку заново для нового вопроса", show_alert=True)


def show_stats(call, bot):
    """Показывает статистику пользователя."""
    user_id = call.from_user.id
    username = call.from_user.username
    stats = data_manager.get_user_stats(user_id, username)
    solved_count = data_manager.get_user_solved_words_count(user_id)
    
    correct = stats['correct_answers']
    streak = stats['streak']
    max_streak = stats['max_streak']
    
    text = (
        f"Ваша статистика\n\n"
        f"Освоено слов: {solved_count}\n\n"
        f"Правильных ответов: {correct}\n\n"
        f"Текущая серия: {streak}\n"
        f"Лучшая серия: {max_streak}"
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def show_leaderboard(call, bot):
    """Показывает таблицу лидеров."""
    leaderboard = data_manager.get_leaderboard(limit=10)
    
    if not leaderboard:
        try:
            bot.edit_message_text(
                "Таблица лидеров\n\n"
                "Пока нет участников. Станьте первым!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_leaderboard_keyboard()
            )
        except Exception as e:
            bot.send_message(
                call.message.chat.id,
                "Таблица лидеров\n\n"
                "Пока нет участников. Станьте первым!",
                reply_markup=get_leaderboard_keyboard()
            )
        return
    
    text = "Таблица лидеров\n\n"
    for entry in leaderboard:
        username = entry['username'] or f"User {entry['user_id']}"
        text += f"{entry['rank']}. {username} — {entry['correct_answers']} правильных\n"
    
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_leaderboard_keyboard()
        )
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=get_leaderboard_keyboard()
        )

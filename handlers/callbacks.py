"""
Обработчики callback-запросов (нажатия на инлайн-кнопки).
"""

from keyboards.inline import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard
)
from utils.data_manager import DataManager
from handlers.text_handler import current_questions

data_manager = DataManager()


def show_main_menu(call, bot):
    """Показывает главное меню."""
    bot.edit_message_text(
        "🏠 Главное меню\n\nВыберите режим работы:",
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
    
    # Формируем текст с 5 предложениями
    sentences_text = ""
    for i, sentence in enumerate(question['sentences'], 1):
        sentences_text += f"{i}. {sentence}\n"
    
    bot.edit_message_text(
        f"📝 Задание 5 ЕГЭ\n\n"
        f"В одном из предложений НЕВЕРНО употреблено выделенное слово.\n"
        f"Исправьте ошибку и напишите правильное слово.\n\n"
        f"{sentences_text}\n"
        f"💡 Напишите правильное слово в чат",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def handle_answer(call, bot):
    """Обрабатывает ответ пользователя на вопрос (теперь не используется - ответ текстовый)."""
    bot.answer_callback_query(call.id, "Напишите ответ текстом в чат", show_alert=True)


def next_question(call, bot):
    """Показывает следующий вопрос."""
    # Для текстового ввода next_question больше не нужен
    bot.answer_callback_query(call.id, "Начните тренировку заново для нового вопроса", show_alert=True)


def show_stats(call, bot):
    """Показывает статистику пользователя."""
    user_id = call.from_user.id
    username = call.from_user.username
    stats = data_manager.get_user_stats(user_id, username)
    
    correct = stats['correct_answers']
    
    text = (
        f"Ваша статистика\n\n"
        f"Правильных ответов: {correct}"
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def show_leaderboard(call, bot):
    """Показывает таблицу лидеров."""
    leaderboard = data_manager.get_leaderboard(limit=20)
    
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
        text += f"{entry['rank']}. {username} — {entry['correct_answers']}\n"
    
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

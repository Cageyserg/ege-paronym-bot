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

# Хранилище состояний пользователей (для тренировки)
user_states = {}


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
    
    # Устанавливаем флаг, что пользователь ожидает ввод ответа
    user_states[user_id] = "waiting_for_answer"
    
    bot.edit_message_text(
        f"📚 Тренировка\n\n"
        f"Вставьте правильное слово:\n\n"
        f"{question['sentence']}\n\n"
        f"💡 Варианты: {', '.join(question['words'])}\n\n"
        f"📝 Введите слово:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def handle_answer(call, bot):
    """Обрабатывает ответ пользователя на вопрос (для callback кнопок)."""
    # Этот обработчик больше не нужен, так как ответы вводятся текстом
    bot.answer_callback_query(call.id, "Теперь введите слово текстом!", show_alert=True)


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
        f"📊 Ваша статистика\n\n"
        f"📚 Освоено слов: {solved_count}\n\n"
        f"✅ Правильных ответов: {correct}\n\n"
        f"🔥 Текущая серия: {streak}\n"
        f"🏆 Лучшая серия: {max_streak}"
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
                "🏆 Таблица лидеров\n\n"
                "Пока нет участников. Станьте первым!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_leaderboard_keyboard()
            )
        except Exception as e:
            bot.send_message(
                call.message.chat.id,
                "🏆 Таблица лидеров\n\n"
                "Пока нет участников. Станьте первым!",
                reply_markup=get_leaderboard_keyboard()
            )
        return
    
    text = "🏆 Таблица лидеров\n\n"
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

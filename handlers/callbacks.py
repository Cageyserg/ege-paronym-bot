"""
Обработчики callback-запросов (нажатия на инлайн-кнопки).
Использует глобальный data_manager из utils.data_manager.
"""

from keyboards.inline import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard,
    get_answer_keyboard
)
# Глобальный data_manager с кэшированием и flush-циклом
from utils.data_manager import data_manager
# Хранилище текущих вопросов пользователей
from handlers.text_handler import current_questions

# Хранилище message_id для таблицы лидеров (chat_id -> message_id)
leaderboard_message_ids = {}


def show_main_menu(call, bot):
    """Показывает главное меню."""
    bot.edit_message_text(
        "*🏠 Главное меню*\n\nВыберите режим работы:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


def start_training(call, bot):
    """Начинает режим тренировки."""
    user_id = call.from_user.id
    # Вопрос берётся из RAM (paronyms.json загружен при старте)
    question = data_manager.get_random_question()

    if not question:
        bot.answer_callback_query(call.id, "Нет доступных вопросов!", show_alert=True)
        return

    current_questions[user_id] = question

    bot.edit_message_text(
        f"📝 Выберите правильное слово\n\n"
        f"{question['task']}\n\n"
        f"💡 Выберите вариант ответа",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_answer_keyboard(question['options'])
    )


def handle_answer(call, bot):
    """Обрабатывает ответ пользователя.
    
    Статистика обновляется ТОЛЬКО В ПАМЯТИ (через StatsCache).
    Запись в БД происходит батчами каждые 10 секунд.
    """
    user_id = call.from_user.id
    username = call.from_user.username
    firstname = call.from_user.first_name

    user_answer = call.data.replace("answer_", "")

    if user_id not in current_questions:
        bot.answer_callback_query(call.id, "Сначала начните тренировку!", show_alert=True)
        return

    question = current_questions[user_id]
    correct_answer = question['correct_answer']
    explanation = question['explanation']

    # Проверяем ответ
    is_correct = user_answer.lower() == correct_answer.lower()

    # Обновляем статистику В ПАМЯТИ (без обращения к БД)
    data_manager.update_user_stats(user_id, is_correct, username, firstname, question['id'], correct_answer)

    if is_correct:
        response_text = (
            f"✅ Правильно!\n\n"
            f"Правильный ответ: *{correct_answer}*\n\n"
            f"📖 {explanation}"
        )

        bot.edit_message_text(
            response_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='Markdown'
        )

        next_question = data_manager.get_random_question()

        if next_question:
            current_questions[user_id] = next_question
            bot.send_message(
                call.message.chat.id,
                f"📝 Выберите правильное слово\n\n"
                f"{next_question['task']}\n\n"
                f"💡 Выберите вариант ответа",
                reply_markup=get_answer_keyboard(next_question['options'])
            )
    else:
        bot.answer_callback_query(
            call.id,
            f"❌ Неправильно!\n\nПопробуйте ещё раз!",
            show_alert=True
        )


def show_stats(call, bot):
    """Показывает статистику пользователя из кэша."""
    user_id = call.from_user.id
    username = call.from_user.username
    firstname = call.from_user.first_name
    stats = data_manager.get_user_stats(user_id, username, firstname)

    correct = stats['correct_answers']
    display_username = stats.get('username', username or 'Anonymous')
    display_firstname = stats.get('firstname', firstname or '')

    if display_firstname:
        user_info = f"@{display_username} ({display_firstname})"
    else:
        user_info = f"@{display_username}"

    text = (
        f"*Ваша статистика*\n\n"
        f"Пользователь: {user_info}\n"
        f"Правильных ответов: {correct}"
    )

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode='Markdown'
    )


def show_leaderboard(call, bot):
    """Показывает таблицу лидеров из кэша."""
    chat_id = call.message.chat.id
    leaderboard = data_manager.get_leaderboard(limit=20)

    if chat_id in leaderboard_message_ids:
        try:
            bot.delete_message(chat_id, leaderboard_message_ids[chat_id])
        except Exception as e:
            pass
        del leaderboard_message_ids[chat_id]

    if not leaderboard:
        msg = bot.send_message(
            chat_id,
            "*Таблица лидеров*\n\n"
            "Пока нет участников. Станьте первым!",
            reply_markup=get_leaderboard_keyboard(),
            parse_mode='Markdown'
        )
        leaderboard_message_ids[chat_id] = msg.message_id
        return

    text = "*Таблица лидеров*\n\n"
    for entry in leaderboard:
        username = entry['username'] or f"User {entry['user_id']}"
        text += f"{entry['rank']}. {username} — {entry['correct_answers']}\n"

    msg = bot.send_message(
        chat_id,
        text,
        reply_markup=get_leaderboard_keyboard(),
        parse_mode='Markdown'
    )
    leaderboard_message_ids[chat_id] = msg.message_id

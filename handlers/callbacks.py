"""
Обработчики callback-запросов (нажатия на инлайн-кнопки).
"""

from keyboards.inline import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard,
    get_answer_keyboard
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

    bot.edit_message_text(
        f"📝 Выберите правильное слово\n\n"
        f"{question['task']}\n\n"
        f"💡 Выберите вариант ответа",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_answer_keyboard(question['options'])
    )


def handle_answer(call, bot):
    """Обрабатывает ответ пользователя на вопрос."""
    user_id = call.from_user.id
    username = call.from_user.username

    # Извлекаем ответ из callback_data
    user_answer = call.data.replace("answer_", "")

    # Получаем текущий вопрос
    if user_id not in current_questions:
        bot.answer_callback_query(call.id, "Сначала начните тренировку!", show_alert=True)
        return

    question = current_questions[user_id]
    correct_answer = question['correct_answer']
    explanation = question['explanation']

    # Проверяем ответ
    is_correct = user_answer.lower() == correct_answer.lower()

    # Обновляем статистику
    data_manager.update_user_stats(user_id, is_correct, username, question['id'], correct_answer)

    if is_correct:
        # При правильном ответе показываем объяснение и переходим к следующему вопросу
        response_text = (
            f"✅ Правильно!\n\n"
            f"Правильный ответ: {correct_answer}\n\n"
            f"📖 {explanation}"
        )

        # Изменяем текущее сообщение на результат
        bot.edit_message_text(
            response_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_back_to_menu_keyboard()
        )

        # Получаем следующий вопрос
        next_question = data_manager.get_random_question()

        if next_question:
            # Сохраняем новый вопрос
            current_questions[user_id] = next_question

            # Отправляем новое сообщение со следующим заданием
            bot.send_message(
                call.message.chat.id,
                f"📝 Выберите правильное слово\n\n"
                f"{next_question['task']}\n\n"
                f"💡 Выберите вариант ответа",
                reply_markup=get_answer_keyboard(next_question['options'])
            )
    else:
        # При неправильном ответе показываем плашку с ошибкой, но вопрос не меняем
        bot.answer_callback_query(
            call.id,
            f"❌ Неправильно!\n\nПопробуйте ещё раз!",
            show_alert=True
        )


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

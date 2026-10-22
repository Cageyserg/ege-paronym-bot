"""
Обработчики callback-запросов (нажатия на инлайн-кнопки).
"""

from keyboards.inline import (
    get_main_menu_keyboard,
    get_training_answer_keyboard,
    get_back_to_menu_keyboard,
    get_dictionary_navigation_keyboard,
    get_leaderboard_keyboard
)
from utils.data_manager import DataManager

data_manager = DataManager()

# Хранилище текущих вопросов пользователей
current_questions = {}


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
        f"📚 Тренировка\n\n"
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
    data_manager.update_user_stats(user_id, is_correct, username)
    
    if is_correct:
        response_text = (
            f"✅ Правильно!\n\n"
            f"Ответ: {question['correct']}\n"
            f"{question['explanation']}"
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
    
    bot.edit_message_text(
        response_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def next_question(call, bot):
    """Показывает следующий вопрос."""
    start_training(call, bot)


def show_dictionary(call, bot):
    """Показывает первую страницу словаря."""
    paronyms = data_manager.get_all_paronyms()
    
    if not paronyms:
        bot.answer_callback_query(call.id, "Словарь пуст!", show_alert=True)
        return
    
    show_paronym_page(call, bot, 0)


def dict_prev_page(call, bot):
    """Показывает предыдущую страницу словаря."""
    current_index = int(call.data.split("_")[2])
    show_paronym_page(call, bot, current_index - 1)


def dict_next_page(call, bot):
    """Показывает следующую страницу словаря."""
    current_index = int(call.data.split("_")[2])
    show_paronym_page(call, bot, current_index + 1)


def show_paronym_page(call, bot, index):
    """Показывает страницу словаря с указанным индексом."""
    paronyms = data_manager.get_all_paronyms()
    
    if index < 0 or index >= len(paronyms):
        bot.answer_callback_query(call.id, "Некорректный индекс", show_alert=True)
        return
    
    paronym = paronyms[index]
    words = paronym['words']
    
    text = (
        f"📖 Словарь паронимов\n\n"
        f"Пара: {words[0]} — {words[1]}\n\n"
        f"Значения:\n"
        f"• {words[0]}: {paronym['definitions'][words[0]]}\n"
        f"• {words[1]}: {paronym['definitions'][words[1]]}\n\n"
        f"Примеры:\n"
        f"• {words[0]}: {paronym['examples'][words[0]]}\n"
        f"• {words[1]}: {paronym['examples'][words[1]]}"
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_dictionary_navigation_keyboard(index, len(paronyms))
    )


def show_stats(call, bot):
    """Показывает статистику пользователя."""
    user_id = call.from_user.id
    username = call.from_user.username
    stats = data_manager.get_user_stats(user_id, username)
    
    total = stats['total_answers']
    correct = stats['correct_answers']
    incorrect = stats['incorrect_answers']
    streak = stats['streak']
    max_streak = stats['max_streak']
    
    if total == 0:
        percentage = 0
    else:
        percentage = round((correct / total) * 100, 1)
    
    text = (
        f"📊 Ваша статистика\n\n"
        f"Всего ответов: {total}\n"
        f"Правильных: {correct}\n"
        f"Неправильных: {incorrect}\n"
        f"Процент правильных: {percentage}%\n\n"
        f"Текущая серия: {streak}\n"
        f"Лучшая серия: {max_streak}"
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def show_check_text_instruction(call, bot):
    """Показывает инструкцию для проверки текста."""
    bot.edit_message_text(
        "🔍 Проверка текста\n\n"
        "Отправьте мне предложение с пропуском (используйте _____ для пропуска), "
        "и я проверю, какой пароним нужно вставить.\n\n"
        "Пример: Я _____ пальто и вышел на улицу.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )


def show_leaderboard(call, bot):
    """Показывает таблицу лидеров."""
    leaderboard = data_manager.get_leaderboard(limit=10)
    
    if not leaderboard:
        bot.edit_message_text(
            "🏆 Таблица лидеров\n\n"
            "Пока нет участников. Станьте первым!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_leaderboard_keyboard()
        )
        return
    
    text = "🏆 Таблица лидеров\n\n"
    for entry in leaderboard:
        text += (
            f"{entry['rank']}. {entry['username']}\n"
            f"   ✅ {entry['correct_answers']} правильных ({entry['percentage']}%)\n"
            f"   🔥 Лучшая серия: {entry['max_streak']}\n\n"
        )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_leaderboard_keyboard()
    )

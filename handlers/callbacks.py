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
        text += (
            f"{entry['rank']}. {username}\n"
            f"   ✅ {entry['correct_answers']} правильных\n"
            f"   🔥 Лучшая серия: {entry['max_streak']}\n\n"
        )
    
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

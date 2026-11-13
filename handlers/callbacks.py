"""
Обработчики callback-запросов.
Тренировка: следующее задание открывается только после верного ответа.
Неверный ответ повышает поколение клавиатуры; остаток очереди кликов
по старым кнопкам молча отбрасывается (анти-брутфорс).
"""

import logging
import threading

from keyboards.inline import (
    get_main_menu_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard,
    get_answer_keyboard,
)
from utils.data_manager import data_manager
from handlers.text_handler import current_questions

logger = logging.getLogger(__name__)

leaderboard_message_ids = {}

_locks = {}
_locks_guard = threading.Lock()


def _get_lock(user_id):
    with _locks_guard:
        if user_id not in _locks:
            _locks[user_id] = threading.Lock()
        return _locks[user_id]


def _md(value):
    return str(value).replace("_", "\\_")


def _new_state(question):
    return {
        "qid": question["id"],
        "attempt": 0,
        "options": list(question["options"]),
        "correct": question["correct_answer"],
        "explanation": question.get("explanation", ""),
        "task": question["task"],
        "done": False,
    }


def _question_text(state):
    return (
        "📝 Выберите правильное слово\n\n"
        f"{state['task']}\n\n"
        "💡 Следующее задание откроется только после верного ответа."
    )


def _refresh_keyboard(bot, chat_id, message_id, state):
    """Новое поколение клавиатуры. Старые кнопки (и клики по ним) мертвы."""
    kb = get_answer_keyboard(state["qid"], state["attempt"], state["options"])
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
        return
    except Exception as e:
        logger.warning(f"edit markup failed: {e}")
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=kb)
        return
    except Exception as e:
        logger.error(f"edit markup retry failed: {e}")
    try:
        bot.send_message(chat_id, _question_text(state), reply_markup=kb)
    except Exception as e:
        logger.error(f"fallback send failed: {e}")


def show_main_menu(call, bot):
    current_questions.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "*🏠 Главное меню*\n\nВыберите режим работы:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


def start_training(call, bot):
    user_id = call.from_user.id
    with _get_lock(user_id):
        question = data_manager.get_random_question()
        if not question:
            bot.answer_callback_query(call.id, "Нет доступных вопросов!", show_alert=True)
            return
        state = _new_state(question)
        current_questions[user_id] = state
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                _question_text(state),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_answer_keyboard(state["qid"], 0, state["options"]),
            )
        except Exception as e:
            logger.warning(f"edit question failed: {e}")


def handle_answer(call, bot):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    try:
        _, qid_s, att_s, idx_s = call.data.split(":")
        qid, attempt, idx = int(qid_s), int(att_s), int(idx_s)
    except (ValueError, AttributeError):
        bot.answer_callback_query(call.id)
        return

    with _get_lock(user_id):
        state = current_questions.get(user_id)

        if state is None or state["done"] or state["qid"] != qid:
            bot.answer_callback_query(call.id)
            return

        # Остаток очереди после неверного ответа: старые кнопки мертвы.
        if state["attempt"] != attempt:
            bot.answer_callback_query(call.id)
            return

        if not (0 <= idx < len(state["options"])):
            bot.answer_callback_query(call.id)
            return

        chosen = state["options"][idx]
        is_correct = chosen.lower() == state["correct"].lower()

        if not is_correct:
            data_manager.update_user_stats(
                user_id, False, call.from_user.username, call.from_user.first_name
            )
            state["attempt"] += 1
            bot.answer_callback_query(call.id, "❌ Неправильно! Попробуй ещё раз.", show_alert=True)
            _refresh_keyboard(bot, chat_id, message_id, state)
            return

        state["done"] = True
        data_manager.update_user_stats(
            user_id, True, call.from_user.username, call.from_user.first_name
        )
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                "✅ Правильно!\n\n"
                f"Правильный ответ: *{_md(state['correct'])}*\n\n"
                f"📖 {_md(state['explanation'])}",
                chat_id, message_id,
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode='Markdown',
            )
        except Exception as e:
            logger.warning(f"edit result failed: {e}")

        next_question = data_manager.get_random_question()
        if next_question is None:
            current_questions.pop(user_id, None)
            bot.send_message(chat_id, "Задания закончились.",
                             reply_markup=get_main_menu_keyboard())
            return

        new_state = _new_state(next_question)
        current_questions[user_id] = new_state
        bot.send_message(
            chat_id,
            _question_text(new_state),
            reply_markup=get_answer_keyboard(new_state["qid"], 0, new_state["options"]),
        )


def handle_legacy_answer(call, bot):
    """Кнопки из сообщений, отправленных до обновления (callback_data='answer_слово')."""
    bot.answer_callback_query(
        call.id,
        "Кнопки из старой версии. Нажми «Тренировка», чтобы получить задание.",
        show_alert=True,
    )
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass


def show_stats(call, bot):
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
    chat_id = call.message.chat.id
    leaderboard = data_manager.get_leaderboard(limit=20)

    if chat_id in leaderboard_message_ids:
        try:
            bot.delete_message(chat_id, leaderboard_message_ids[chat_id])
        except Exception:
            pass
        del leaderboard_message_ids[chat_id]

    if not leaderboard:
        msg = bot.send_message(
            chat_id,
            "*Таблица лидеров*\n\nПока нет участников. Станьте первым!",
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

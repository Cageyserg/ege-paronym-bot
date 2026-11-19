"""
Обработчики callback-запросов: меню, тренировка, статистика, лидерборд.

Правила тренировки:
- следующее задание открывается только после верного ответа;
- неверный ответ повышает поколение клавиатуры, поэтому остаток очереди
  кликов по старым кнопкам молча отбрасывается (анти-брутфорс);
- на каждый callback обязателен ответ, иначе кнопка «крутится» у пользователя.
"""

import contextlib
import logging

from config import MAX_TRACKED_USERS
from handlers.state import BoundedDict, QuizStore, new_state
from keyboards.inline import (
    get_answer_keyboard,
    get_back_to_menu_keyboard,
    get_leaderboard_keyboard,
    get_main_menu_keyboard,
)
from utils.data_manager import data_manager
from utils.formatting import (
    code_safe,
    display_width,
    md_escape,
    pad_width,
    truncate_width,
    user_label,
)

logger = logging.getLogger(__name__)

# Активные задания пользователей и их блокировки (ограничены по размеру).
quiz = QuizStore(max_users=MAX_TRACKED_USERS)

# id последнего сообщения с таблицей лидеров на каждый чат (ограничено по размеру).
leaderboard_message_ids = BoundedDict(maxsize=1000)

# Сколько участников показывать в таблице лидеров.
LEADERBOARD_LIMIT = 20


def _record_answer(user_id: int, is_correct: bool, user) -> None:
    """
    Пишет ответ в MongoDB. Сбой хранилища не должен ломать тренировку:
    пользователь всё равно получает реакцию на клик.
    """
    try:
        data_manager.update_user_stats(user_id, is_correct,
                                       getattr(user, "username", None),
                                       getattr(user, "first_name", None))
    except Exception as e:
        logger.error("Не удалось записать ответ в MongoDB (user_id=%s): %s", user_id, e)


def question_text(state: dict) -> str:
    """Текст сообщения с заданием."""
    return (
        "📝 Выберите правильное слово\n\n"
        f"{state['task']}\n\n"
        "💡 Следующее задание откроется только после верного ответа."
    )


def _safe_answer(bot, call, text: str | None = None, alert: bool = False):
    """Отвечает на callback, не падая на устаревших запросах."""
    try:
        if text:
            bot.answer_callback_query(call.id, text, show_alert=alert)
        else:
            bot.answer_callback_query(call.id)
    except Exception as e:  # устаревший callback_id — не повод падать
        logger.debug("answer_callback_query failed: %s", e)


def _edit_text(bot, chat_id: int, message_id: int, text: str,
               markup=None, parse_mode: str | None = None) -> bool:
    """Редактирует сообщение; при ошибке сообщает False."""
    try:
        bot.edit_message_text(text, chat_id, message_id,
                              reply_markup=markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.warning("edit_message_text failed: %s", e)
        return False


def _refresh_keyboard(bot, chat_id: int, message_id: int, state: dict):
    """Новое поколение клавиатуры: старые кнопки перестают работать."""
    markup = get_answer_keyboard(state["qid"], state["attempt"], state["options"])
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
        return
    except Exception as e:
        logger.warning("edit_message_reply_markup failed: %s", e)
    try:
        bot.send_message(chat_id, question_text(state), reply_markup=markup)
    except Exception as e:
        logger.error("fallback send failed: %s", e)


def _next_question(bot, chat_id: int, user_id: int):
    """Выдаёт следующее задание или завершает тренировку."""
    question = data_manager.get_random_question()
    if question is None:
        quiz.pop(user_id)
        bot.send_message(chat_id, "Задания закончились.",
                         reply_markup=get_main_menu_keyboard())
        return
    state = new_state(question)
    quiz.set(user_id, state)
    bot.send_message(
        chat_id,
        question_text(state),
        reply_markup=get_answer_keyboard(state["qid"], 0, state["options"]),
    )


def show_main_menu(call, bot):
    quiz.pop(call.from_user.id)
    _safe_answer(bot, call)
    _edit_text(
        bot, call.message.chat.id, call.message.message_id,
        "*🏠 Главное меню*\n\nВыберите режим работы:",
        markup=get_main_menu_keyboard(), parse_mode="Markdown",
    )


def start_training(call, bot):
    user_id = call.from_user.id
    with quiz.lock_for(user_id):
        question = data_manager.get_random_question()
        if not question:
            _safe_answer(bot, call, "Нет доступных заданий!", alert=True)
            return
        state = new_state(question)
        quiz.set(user_id, state)
        _safe_answer(bot, call)
        if not _edit_text(
            bot, call.message.chat.id, call.message.message_id, question_text(state),
            markup=get_answer_keyboard(state["qid"], 0, state["options"]),
        ):
            # Сообщение могло быть удалено — отправляем новое.
            _next_question(bot, call.message.chat.id, user_id)


def handle_answer(call, bot):
    """Обрабатывает нажатие на вариант ответа."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    try:
        _, qid_s, att_s, idx_s = call.data.split(":")
        qid, attempt, idx = int(qid_s), int(att_s), int(idx_s)
    except (ValueError, AttributeError):
        _safe_answer(bot, call)
        return

    with quiz.lock_for(user_id):
        state = quiz.get(user_id)
        if state is None or state["done"] or state["qid"] != qid:
            _safe_answer(bot, call)
            return
        # Клик по кнопке предыдущего поколения — молча игнорируем.
        if state["attempt"] != attempt:
            _safe_answer(bot, call)
            return
        if not 0 <= idx < len(state["options"]):
            _safe_answer(bot, call)
            return

        chosen = state["options"][idx]
        is_correct = chosen.strip().lower() == state["correct"].strip().lower()
        user = call.from_user

        if not is_correct:
            _record_answer(user_id, False, user)
            state["attempt"] += 1
            _safe_answer(bot, call, "❌ Неправильно! Попробуй ещё раз.", alert=True)
            _refresh_keyboard(bot, chat_id, message_id, state)
            return

        state["done"] = True
        _record_answer(user_id, True, user)
        _safe_answer(bot, call)
        _edit_text(
            bot, chat_id, message_id,
            "✅ Правильно!\n\n"
            f"Правильный ответ: *{md_escape(state['correct'])}*\n\n"
            f"📖 {md_escape(state['explanation'])}",
            markup=get_back_to_menu_keyboard(), parse_mode="Markdown",
        )
        _next_question(bot, chat_id, user_id)


def handle_legacy_answer(call, bot):
    """Кнопки из сообщений, отправленных до обновления (callback_data='answer_...')."""
    _safe_answer(
        bot, call,
        "Кнопки из старой версии. Нажми «Тренировка», чтобы получить задание.",
        alert=True,
    )
    with contextlib.suppress(Exception):
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=None)


def stats_text(stats: dict) -> str:
    """Текст экрана статистики."""
    label = user_label(stats.get("username"), stats.get("firstname"))
    correct = stats.get("correct_answers", 0)
    total = stats.get("total_answers", correct)
    percent = round(correct * 100.0 / total, 1) if total else 0.0
    return (
        "*Ваша статистика*\n\n"
        f"Пользователь: {md_escape(label)}\n"
        f"Правильных ответов: {correct}\n"
        f"Всего ответов: {total}\n"
        f"Точность: {percent}%\n"
        f"Лучшая серия: {stats.get('max_streak', 0)}"
    )


def show_stats(call, bot):
    user = call.from_user
    try:
        stats = data_manager.get_user_stats(user.id, user.username, user.first_name)
    except Exception as e:
        logger.error("Статистика недоступна (user_id=%s): %s", user.id, e)
        _safe_answer(bot, call, "Статистика временно недоступна. Попробуй позже.",
                     alert=True)
        return
    _safe_answer(bot, call)
    _edit_text(
        bot, call.message.chat.id, call.message.message_id, stats_text(stats),
        markup=get_back_to_menu_keyboard(), parse_mode="Markdown",
    )


# Максимальная ширина имени в клетках моноширинного шрифта.
# Имя обрезается, цифры прижимаются вправо — тогда столбцы не «пляшут».
NAME_WIDTH = 18

# Ширины числовых колонок не фиксированы: они подстраиваются под самые длинные
# значения в текущей таблице, поэтому 5-6-значные счётчики не ломают выравнивание.
NUM_WIDTH = 4


def leaderboard_name(entry: dict) -> str:
    """Имя участника, подготовленное для ```-блока: без разметки, обрезано по ширине."""
    raw = entry.get("display_name") or entry.get("username") or "Без имени"
    return truncate_width(code_safe(raw), NAME_WIDTH)


def _column_widths(entries) -> tuple[int, int, int]:
    """
    Ширины колонок под конкретную таблицу.

    Ранг и счётчики меряются по фактическим значениям, поэтому появление
    «1000» или «100000» не сдвигает столбцы относительно коротких чисел.
    """
    rank_width = max((display_width(str(entry.get("rank", 0))) for entry in entries),
                     default=1)
    correct_width = max(
        (display_width(str(entry.get("correct_answers", 0))) for entry in entries),
        default=1,
    )
    streak_width = max(
        (display_width(str(entry.get("max_streak", 0))) for entry in entries),
        default=1,
    )
    return (
        max(rank_width, 1),
        max(correct_width, NUM_WIDTH),
        max(streak_width, NUM_WIDTH),
    )


def leaderboard_entry(entry: dict, widths: tuple[int, int, int] | None = None) -> str:
    """
    Одна строка таблицы лидеров, выровненная по колонкам.

    Пример:
         3. Cageyserg     —  112 | 🔗  15

    Слева — всего верных ответов, справа после 🔗 — лучшая серия подряд.
    """
    rank_width, correct_width, streak_width = widths or _column_widths([entry])
    name = pad_width(leaderboard_name(entry), NAME_WIDTH)
    correct = str(entry.get("correct_answers", 0)).rjust(correct_width)
    streak = str(entry.get("max_streak", 0)).rjust(streak_width)
    rank = str(entry.get("rank", 0)).rjust(rank_width)
    return f"{rank}. {name} — {correct} | 🔗 {streak}"


def leaderboard_text(entries) -> str:
    """
    Текст таблицы лидеров.

    Колонки выравниваются пробелами внутри ```-блока: в обычном тексте
    Telegram использует пропорциональный шрифт, и цифры встают лесенкой.
    Ширины подбираются под конкретные значения, поэтому таблица остаётся
    ровной при любом числе участников и любой длине имён.

    Для каждого участника показываются два показателя:
    - всего верных ответов;
    - лучшая серия (🔗) — максимальное число верных ответов подряд.
    """
    entries = list(entries)
    if not entries:
        return "*🏆 Таблица лидеров*\n\nПока нет участников. Станьте первым!"
    widths = _column_widths(entries)
    rows = "\n".join(leaderboard_entry(entry, widths) for entry in entries)
    return (
        "*🏆 Таблица лидеров*\n\n"
        f"```\n{rows}\n```\n\n"
        "_верных | 🔗 серия — максимум подряд_"
    )


def _delete_previous_leaderboard(bot, chat_id: int):
    """Удаляет прошлое сообщение с таблицей лидеров в этом чате."""
    old_id = leaderboard_message_ids.get_lru(chat_id)
    if old_id is None:
        return
    with contextlib.suppress(Exception):
        bot.delete_message(chat_id, old_id)
    leaderboard_message_ids.pop(chat_id, None)


def send_leaderboard(bot, chat_id: int) -> bool:
    """Отправляет таблицу лидеров и запоминает id сообщения."""
    try:
        entries = data_manager.get_leaderboard(limit=LEADERBOARD_LIMIT)
    except Exception as e:
        logger.error("Таблица лидеров недоступна: %s", e)
        try:
            bot.send_message(chat_id, "Таблица лидеров временно недоступна. Попробуй позже.")
        except Exception as send_error:
            logger.error("Не удалось сообщить об ошибке лидерборда: %s", send_error)
        return False
    _delete_previous_leaderboard(bot, chat_id)
    msg = bot.send_message(
        chat_id,
        leaderboard_text(entries),
        reply_markup=get_leaderboard_keyboard(),
        parse_mode="Markdown",
    )
    leaderboard_message_ids[chat_id] = msg.message_id


def show_leaderboard(call, bot):
    _safe_answer(bot, call)
    send_leaderboard(bot, call.message.chat.id)

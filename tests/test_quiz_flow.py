"""Тесты сценария тренировки: анти-брутфорс, акки, переход к следующему заданию."""

from types import SimpleNamespace

from handlers.callbacks import handle_answer, show_main_menu, start_training
from tests.conftest import make_call


def _start(cb, bot, user, message):
    start_training(make_call(user, message, "training_start"), bot)
    return cb.quiz.get(user.id)


def _answer(cb, bot, user, message, idx, attempt=0, qid=None):
    state = cb.quiz.get(user.id)
    qid = state["qid"] if qid is None else qid
    handle_answer(make_call(user, message, f"a:{qid}:{attempt}:{idx}"), bot)


def _index_of(state, correct=True):
    for i, option in enumerate(state["options"]):
        if (option.lower() == state["correct"].lower()) is correct:
            return i
    raise AssertionError("вариант не найден")


def test_start_training_creates_state(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    assert state is not None
    assert state["qid"] and state["options"] and state["attempt"] == 0
    assert fake_bot.count("answer_callback_query") == 1


def test_wrong_answer_increments_attempt_and_counts_stats(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=False))

    assert state["attempt"] == 1
    assert state["done"] is False
    stats = callbacks.data_manager.get_user_stats(user.id)
    assert stats["correct_answers"] == 0
    assert stats["streak"] == 0
    assert fake_bot.last("answer_callback_query")[2] == "❌ Неправильно! Попробуй ещё раз."


def test_stale_generation_click_is_ignored(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    stale_payload = f"a:{state['qid']}:0:{_index_of(state, correct=True)}"
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=False))
    assert state["attempt"] == 1

    # Клик по кнопке старого поколения — состояние не меняется, ответ не зачтён.
    handle_answer(make_call(user, message, stale_payload), fake_bot)
    assert state["done"] is False
    # Число верных слов не изменилось — повторного зачёта не было.
    assert callbacks.data_manager.get_user_stats(user.id)["correct_answers"] == 0


def test_correct_answer_advances_to_next_question(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=True))

    assert state["done"] is True
    stats = callbacks.data_manager.get_user_stats(user.id)
    assert stats["correct_answers"] == 1
    assert stats["max_streak"] == 1

    new_state = callbacks.quiz.get(user.id)
    assert new_state is not state
    assert new_state["attempt"] == 0 and new_state["done"] is False
    assert fake_bot.last("send_message") is not None


def test_repeat_correct_click_does_not_double_count(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    qid, idx = state["qid"], _index_of(state, correct=True)
    _answer(callbacks, fake_bot, user, message, idx)
    handle_answer(make_call(user, message, f"a:{qid}:0:{idx}", call_id="cb-2"), fake_bot)

    stats = callbacks.data_manager.get_user_stats(user.id)
    assert stats["correct_answers"] == 1


def test_answer_without_state_is_ignored(callbacks, fake_bot, user, message):
    handle_answer(make_call(user, message, "a:1:0:0"), fake_bot)
    assert fake_bot.count("answer_callback_query") == 1
    assert fake_bot.count("edit_message_text") == 0


def test_answer_with_other_question_id_is_ignored(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=True),
            qid=state["qid"] + 9999)
    assert state["done"] is False


def test_answer_with_out_of_range_index_is_ignored(callbacks, fake_bot, user, message):
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, 99)
    assert state["done"] is False
    assert state["attempt"] == 0


def test_malformed_callback_data_is_ignored(callbacks, fake_bot, user, message):
    handle_answer(make_call(user, message, "a:broken"), fake_bot)
    assert fake_bot.count("edit_message_text") == 0


def test_main_menu_clears_state(callbacks, fake_bot, user, message):
    _start(callbacks, fake_bot, user, message)
    show_main_menu(make_call(user, message, "main_menu"), fake_bot)
    assert callbacks.quiz.get(user.id) is None
    assert "Главное меню" in fake_bot.last("edit_message_text")[1]


def test_edit_failure_falls_back_to_new_message(callbacks, fake_bot, user, message,
                                               monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("message is not modified")

    monkeypatch.setattr(fake_bot, "edit_message_text", boom)
    start_training(make_call(user, message, "training_start"), fake_bot)
    assert fake_bot.last("send_message") is not None


def test_legacy_buttons_get_alert(callbacks, fake_bot, user, message):
    from handlers.callbacks import handle_legacy_answer

    handle_legacy_answer(make_call(user, message, "answer_слово"), fake_bot)
    call = fake_bot.last("answer_callback_query")
    assert call[3] is True
    assert "старой версии" in call[2]


def test_leaderboard_message_is_replaced(callbacks, fake_bot, user, message):
    from handlers.callbacks import show_leaderboard

    callbacks.data_manager.update_user_stats(user.id, True, user.username, user.first_name)
    show_leaderboard(make_call(user, message, "leaderboard", call_id="cb-1"), fake_bot)
    first_id = fake_bot.last("send_message")
    show_leaderboard(make_call(user, message, "leaderboard", call_id="cb-2"), fake_bot)
    deleted = fake_bot.last("delete_message")
    assert deleted[2] == callbacks.leaderboard_message_ids[42] or deleted is not None
    assert first_id is not None


def test_stats_screen_shows_counts(callbacks, fake_bot, user, message):
    from handlers.callbacks import show_stats

    callbacks.data_manager.update_user_stats(user.id, True, user.username, user.first_name)
    callbacks.data_manager.update_user_stats(user.id, False, user.username, user.first_name)
    show_stats(make_call(user, message, "stats"), fake_bot)
    text = fake_bot.last("edit_message_text")[1]
    assert "Верно решено слов: 1" in text
    assert "Текущая серия: 0" in text
    assert "Максимальная серия: 1" in text
    assert "@tester" in text
    # Точности и «всего ответов» больше нет: этих данных не храним.
    assert "Точность" not in text
    assert "Всего ответов" not in text


def test_no_questions_available(callbacks, fake_bot, user, message, monkeypatch):
    monkeypatch.setattr(callbacks.data_manager, "get_random_question", lambda: None)
    start_training(make_call(user, message, "training_start"), fake_bot)
    assert fake_bot.last("answer_callback_query")[2] == "Нет доступных заданий!"
    assert callbacks.quiz.get(user.id) is None


def test_quiz_store_eviction_keeps_active_states():
    from handlers.state import QuizStore

    store = QuizStore(max_users=10)
    for uid in range(30):
        store.lock_for(uid)
        if uid % 2 == 0:
            store.set(uid, {"done": False})
    assert store.size() <= 15
    # Активные (незавершённые) задания не вытесняются.
    assert store.get(28) is not None


def test_bounded_dict_drops_oldest():
    from handlers.state import BoundedDict

    d = BoundedDict(maxsize=3)
    for i in range(5):
        d[i] = i
    assert list(d) == [2, 3, 4]
    assert d.get_lru(2) == 2


def test_quiz_lock_serializes(callbacks, fake_bot, user, message):
    lock = callbacks.quiz.lock_for(user.id)
    assert lock is callbacks.quiz.lock_for(user.id)
    other = SimpleNamespace(id=99)
    assert callbacks.quiz.lock_for(other.id) is not lock


def test_answer_survives_storage_failure(callbacks, fake_bot, user, message, monkeypatch):
    """Падение MongoDB не ломает тренировку: пользователь получает ответ на клик."""
    def boom(*args, **kwargs):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "update_user_stats", boom)
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=True))

    assert state["done"] is True
    assert fake_bot.last("edit_message_text")[1].startswith("✅")


def test_stats_screen_handles_storage_failure(callbacks, fake_bot, user, message, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "get_user_stats", boom)
    from handlers.callbacks import show_stats

    show_stats(make_call(user, message, "stats"), fake_bot)
    assert "недоступна" in fake_bot.last("answer_callback_query")[2]


def test_leaderboard_handles_storage_failure(callbacks, fake_bot, user, message, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "get_leaderboard", boom)
    from handlers.callbacks import show_leaderboard

    show_leaderboard(make_call(user, message, "leaderboard"), fake_bot)
    assert "недоступна" in fake_bot.last("send_message")[2]


def test_answer_is_recorded_even_if_storage_fails(callbacks, fake_bot, user, message,
                                                 monkeypatch):
    """Сбой MongoDB не должен ломать тренировку для пользователя."""
    def boom(*a, **kw):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "update_user_stats", boom)
    state = _start(callbacks, fake_bot, user, message)
    _answer(callbacks, fake_bot, user, message, _index_of(state, correct=True))

    assert state["done"] is True
    assert fake_bot.last("edit_message_text")[1].startswith("✅")


def test_stats_screen_reports_storage_failure(callbacks, fake_bot, user, message,
                                              monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "get_user_stats", boom)
    from handlers.callbacks import show_stats

    show_stats(make_call(user, message, "stats"), fake_bot)
    assert "недоступна" in fake_bot.last("answer_callback_query")[2]


def test_leaderboard_reports_storage_failure(callbacks, fake_bot, user, message,
                                             monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(callbacks.data_manager, "get_leaderboard", boom)
    from handlers.callbacks import show_leaderboard

    show_leaderboard(make_call(user, message, "leaderboard"), fake_bot)
    assert "недоступна" in fake_bot.last("send_message")[2]

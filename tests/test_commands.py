"""Тесты команд /start, /help, /top, /count."""

from types import SimpleNamespace

import pytest

from handlers import start as start_mod


@pytest.fixture
def commands(manager, monkeypatch):
    from handlers import callbacks as callbacks_mod

    monkeypatch.setattr(start_mod, "data_manager", manager)
    # send_leaderboard живёт в handlers.callbacks и берёт data_manager оттуда.
    monkeypatch.setattr(callbacks_mod, "data_manager", manager)
    monkeypatch.setattr(callbacks_mod, "leaderboard_message_ids",
                        callbacks_mod.BoundedDict(maxsize=10))
    return start_mod


def _message(user, text="/start"):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=user.id),
        chat_id=user.id,
        from_user=user,
    )


def test_cmd_start_sends_menu(commands, fake_bot, user):
    commands.cmd_start(_message(user), fake_bot)
    call = fake_bot.last("send_message")
    assert "Добро пожаловать" in call[2]
    assert call[3] is not None  # клавиатура приложена
    assert call[4] == "Markdown"


def test_cmd_help_lists_commands(commands, fake_bot, user):
    commands.cmd_help(_message(user, "/help"), fake_bot)
    text = fake_bot.last("send_message")[2]
    for command in ("/start", "/top", "/count", "/help"):
        assert command in text


def test_cmd_count_shows_stats(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, user.username, user.first_name)
    commands.cmd_count(_message(user, "/count"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "Правильных ответов: 1" in text
    assert "@tester" in text


def test_cmd_top_empty_leaderboard(commands, fake_bot, user):
    commands.cmd_top(_message(user, "/top"), fake_bot)
    assert "Пока нет участников" in fake_bot.last("send_message")[2]


def test_cmd_top_lists_users(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, "vasya", "Вася")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "Вася" in text
    assert "—    1 | 🔗    1" in text


def test_cmd_top_shows_max_streak(commands, fake_bot, user, manager):
    """Помимо общего числа верных ответов видна лучшая серия подряд."""
    for _ in range(3):
        manager.update_user_stats(user.id, True, "vasya", "Вася")
    manager.update_user_stats(user.id, False, "vasya", "Вася")
    manager.update_user_stats(user.id, True, "vasya", "Вася")

    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    # 4 верных всего, серия 3 — максимум подряд (текущая после ошибки 1).
    assert "—    4 | 🔗    3" in text
    assert "🔗    1" not in text


def test_cmd_top_legend_explains_columns(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, "vasya", "Вася")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "верных | 🔗 серия — максимум подряд" in text


def test_cmd_top_sanitizes_backticks_in_code_block(commands, fake_bot, user, manager):
    """Имя внутри ```-блока не должно содержать обратных кавычек и переводов строк."""
    manager.update_user_stats(user.id, True, "bad_name", "Ва`ся")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "`" not in text.split("```")[1]
    assert "Ва'ся" in text


def test_commands_survive_telegram_errors(commands, fake_bot, user, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("telegram is down")

    monkeypatch.setattr(fake_bot, "send_message", boom)
    commands.cmd_start(_message(user), fake_bot)   # не должно бросить
    commands.cmd_help(_message(user), fake_bot)
    commands.cmd_top(_message(user), fake_bot)
    commands.cmd_count(_message(user), fake_bot)


def test_leaderboard_entry_matches_reference_format():
    """Формат строки, выровненной по колонкам."""
    from handlers.callbacks import leaderboard_entry

    line = leaderboard_entry({
        "rank": 3, "display_name": "Cageyserg",
        "correct_answers": 112, "max_streak": 15,
    })
    assert line == " 3. Cageyserg          —  112 | 🔗   15"


def test_cmd_top_orders_by_correct_answers(commands, fake_bot, user, storage):
    """Реальные документы Mongo: ранги по верным ответам, серия — вторая колонка."""
    storage._col.insert_many([
        {"user_id": 1, "firstname": "Имя1", "username": "",
         "correct_answers": 112, "total_answers": 130, "streak": 2, "max_streak": 15},
        {"user_id": 2, "firstname": "Имя2", "username": "",
         "correct_answers": 120, "total_answers": 140, "streak": 3, "max_streak": 18},
        {"user_id": 3, "firstname": "Имя3", "username": "",
         "correct_answers": 115, "total_answers": 121, "streak": 0, "max_streak": 16},
    ])
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    lines = [ln for ln in text.splitlines() if ln.strip()[:1].isdigit()]
    assert lines == [
        " 1. Имя2               —  120 | 🔗   18",
        " 2. Имя3               —  115 | 🔗   16",
        " 3. Имя1               —  112 | 🔗   15",
    ]


def test_leaderboard_columns_are_aligned():
    """Префикс «ранг. имя» одинаковой ширины — иначе цифры встают лесенкой."""
    from handlers.callbacks import leaderboard_entry
    from utils.formatting import display_width

    names = ["Пархаева", "Александр (◕‿◕✿)", "Cageyserg", "-M-", "Аскер🍂🌧🦊",
             "Vill Hightopp", "BacioInfiore 🐝", "Яна"]
    widths = {
        display_width(
            leaderboard_entry({
                "rank": rank, "display_name": name,
                "correct_answers": rank * 7, "max_streak": rank,
            }).split("—")[0]
        )
        for rank, name in enumerate(names, 1)
    }
    assert len(widths) == 1


def test_leaderboard_aligns_double_digit_ranks():
    """Ранг 10 не должен сдвигать колонку относительно ранга 1."""
    from handlers.callbacks import leaderboard_entry
    from utils.formatting import display_width

    first = leaderboard_entry({"rank": 1, "display_name": "Яна",
                               "correct_answers": 1, "max_streak": 1})
    tenth = leaderboard_entry({"rank": 10, "display_name": "Яна",
                               "correct_answers": 1, "max_streak": 1})
    assert display_width(first.split("—")[0]) == display_width(tenth.split("—")[0])


def test_leaderboard_long_name_is_truncated():
    """Слишком длинное имя обрезается, чтобы не ломать колонки."""
    from handlers.callbacks import NAME_WIDTH, leaderboard_entry
    from utils.formatting import display_width

    line = leaderboard_entry({
        "rank": 1, "display_name": "Очень-очень длинное имя пользователя",
        "correct_answers": 5, "max_streak": 2,
    })
    assert display_width(line.split("—")[0]) == display_width(
        leaderboard_entry({"rank": 1, "display_name": "Я",
                           "correct_answers": 5, "max_streak": 2}).split("—")[0]
    )
    assert "…" in line
    assert NAME_WIDTH == 18

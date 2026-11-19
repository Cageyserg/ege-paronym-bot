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
    assert "1. 1 | 🔗 1     · *Вася*" in text


def test_cmd_top_shows_max_streak(commands, fake_bot, user, manager):
    """Помимо общего числа верных ответов видна лучшая серия подряд."""
    for _ in range(3):
        manager.update_user_stats(user.id, True, "vasya", "Вася")
    manager.update_user_stats(user.id, False, "vasya", "Вася")
    manager.update_user_stats(user.id, True, "vasya", "Вася")

    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    # 4 верных всего, серия 3 — максимум подряд (текущая после ошибки 1).
    assert "1. 4 | 🔗 3     · *Вася*" in text
    assert "🔗 1 ·" not in text


def test_cmd_top_legend_explains_columns(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, "vasya", "Вася")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "верных | 🔗 серия — максимум подряд" in text


def test_cmd_top_escapes_markdown_in_name(commands, fake_bot, user, manager):
    """Ник с Markdown-символами не должен ломать разметку сообщения."""
    manager.update_user_stats(user.id, True, "bad_name", "Ва`ся_*")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "```" not in text
    assert "Ва\\`ся\\_\\*" in text


def test_commands_survive_telegram_errors(commands, fake_bot, user, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("telegram is down")

    monkeypatch.setattr(fake_bot, "send_message", boom)
    commands.cmd_start(_message(user), fake_bot)   # не должно бросить
    commands.cmd_help(_message(user), fake_bot)
    commands.cmd_top(_message(user), fake_bot)
    commands.cmd_count(_message(user), fake_bot)


def test_leaderboard_entry_format():
    """Строка без выравнивания: ранг, жирное имя, верные и серия через разделители."""
    from handlers.callbacks import leaderboard_entry

    line = leaderboard_entry({
        "rank": 3, "display_name": "Cageyserg",
        "correct_answers": 112, "max_streak": 15,
    })
    assert line == "3. 112 | 🔗 15     · *Cageyserg*"


def test_leaderboard_has_no_code_block():
    """Таблица не должна выглядеть как листинг кода с ```."""
    from handlers.callbacks import leaderboard_text

    text = leaderboard_text([{"rank": 1, "display_name": "Яна",
                              "correct_answers": 7, "max_streak": 3}])
    assert "```" not in text
    assert "`" not in text


def test_leaderboard_separates_name_with_wide_gap():
    """Между серией и именем — заметная отбивка, иначе строка читается слитно."""
    from handlers.callbacks import NAME_GAP, leaderboard_text

    text = leaderboard_text([{"rank": 1, "display_name": "Яна",
                              "correct_answers": 7, "max_streak": 3}])
    row = [ln for ln in text.splitlines() if ln.startswith("1.")][0]
    assert row.endswith(f"{NAME_GAP}· *Яна*")
    assert len(NAME_GAP) >= 4
    assert NAME_GAP.strip() == ""  # только пробелы, иначе выравнивание поедет


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
    lines = [ln for ln in text.splitlines() if ln[:1].isdigit()]
    assert lines == [
        "1. 120 | 🔗 18     · *Имя2*",
        "2. 115 | 🔗 16     · *Имя3*",
        "3. 112 | 🔗 15     · *Имя1*",
    ]


def test_leaderboard_long_name_is_truncated():
    """Слишком длинное имя обрезается, чтобы не растягивать строку."""
    from handlers.callbacks import NAME_WIDTH, leaderboard_entry

    line = leaderboard_entry({
        "rank": 1, "display_name": "Очень-очень длинное имя пользователя",
        "correct_answers": 5, "max_streak": 2,
    })
    assert "…" in line
    name = line.split(" · ")[0].removeprefix("1. ").strip("*")
    assert len(name) <= NAME_WIDTH


def test_leaderboard_handles_six_digit_counters():
    """Большие числа просто печатаются как есть, без выравнивания."""
    from handlers.callbacks import leaderboard_text

    text = leaderboard_text([
        {"rank": 1, "display_name": "Мега", "correct_answers": 123456, "max_streak": 98765},
        {"rank": 2, "display_name": "Яна", "correct_answers": 1, "max_streak": 1},
    ])
    assert "1. 123456 | 🔗 98765     · *Мега*" in text
    assert "2.      1 | 🔗     1     · *Яна*" in text


def test_leaderboard_handles_emoji_nicknames():
    """Эмодзи в нике больше не влияют ни на что: выравнивания нет."""
    from handlers.callbacks import leaderboard_text

    text = leaderboard_text([
        {"rank": 1, "display_name": "Аскер🍂🌧🦊", "correct_answers": 40, "max_streak": 8},
        {"rank": 2, "display_name": "BacioInfiore 🐝", "correct_answers": 5, "max_streak": 4},
    ])
    assert "1. 40 | 🔗 8     · *Аскер🍂🌧🦊*" in text
    assert "2.  5 | 🔗 4     · *BacioInfiore 🐝*" in text


def test_leaderboard_numeric_prefix_has_equal_length():
    """
    Выравнивание держится на том, что имя стоит последним.

    Цифры и пробелы в пропорциональном шрифте Telegram моноширинны, поэтому
    одинаковая длина префикса = одинаковое визуальное выравнивание. Буквы же
    разной ширины — если бы имя было в начале, колонки бы съехали.
    """
    from handlers.callbacks import leaderboard_text

    names = ["Пархаева", "Александр (◕‿◕✿)", "Cageyserg", "-M-", "Аскер🍂🌧🦊",
             "Vill Hightopp", "BacioInfiore 🐝", "Яна"]
    entries = [
        {"rank": i, "display_name": name, "correct_answers": 1000 - i * 7,
         "max_streak": i}
        for i, name in enumerate(names, 1)
    ]
    rows = [ln for ln in leaderboard_text(entries).splitlines() if ln[:1].isdigit()]
    prefixes = {row.split(" · ")[0] for row in rows}
    assert len(prefixes) == len(rows)  # префиксы различаются содержимым
    assert len({len(row.split(" · ")[0]) for row in rows}) == 1


def test_leaderboard_prefix_uses_only_digits_spaces_and_separators():
    """В выравниваемой части не должно быть букв — иначе ширина «поплывёт»."""
    import re

    from handlers.callbacks import leaderboard_text

    text = leaderboard_text([
        {"rank": 1, "display_name": "Ксения", "correct_answers": 41, "max_streak": 20},
        {"rank": 2, "display_name": "Я", "correct_answers": 1, "max_streak": 1},
    ])
    rows = [ln for ln in text.splitlines() if ln[:1].isdigit()]
    for row in rows:
        prefix = row.split(" · ")[0]
        assert re.fullmatch(r"[0-9. |🔗]+", prefix), prefix

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
    assert "1. Вася" in text
    assert "1 верных" in text
    assert "серия 1" in text


def test_cmd_top_shows_max_streak(commands, fake_bot, user, manager):
    """Помимо общего числа верных ответов видна лучшая серия подряд."""
    for _ in range(3):
        manager.update_user_stats(user.id, True, "vasya", "Вася")
    manager.update_user_stats(user.id, False, "vasya", "Вася")
    manager.update_user_stats(user.id, True, "vasya", "Вася")

    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "4 верных" in text       # всего правильных ответов
    assert "серия 3" in text        # максимум подряд, не текущая (она 1)
    assert "серия 1" not in text


def test_cmd_top_legend_explains_columns(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, "vasya", "Вася")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "серия — максимум подряд" in text


def test_cmd_top_escapes_markdown(commands, fake_bot, user, manager):
    manager.update_user_stats(user.id, True, "bad_name", "*Вася*")
    commands.cmd_top(_message(user, "/top"), fake_bot)
    text = fake_bot.last("send_message")[2]
    assert "\\*Вася\\*" in text


def test_commands_survive_telegram_errors(commands, fake_bot, user, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("telegram is down")

    monkeypatch.setattr(fake_bot, "send_message", boom)
    commands.cmd_start(_message(user), fake_bot)   # не должно бросить
    commands.cmd_help(_message(user), fake_bot)
    commands.cmd_top(_message(user), fake_bot)
    commands.cmd_count(_message(user), fake_bot)

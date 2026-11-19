"""Тесты регистрации хендлеров и конфигурации."""

import telebot

import config
from core.bot_core import build_bot, register_handlers


def test_build_bot_registers_commands():
    bot = build_bot("123456:TEST-TOKEN")
    handlers = bot.message_handlers
    commands = {cmd for h in handlers for cmd in (h.get("filters", {}).get("commands") or [])}
    assert {"start", "help", "top", "count"} <= commands


def test_build_bot_registers_callbacks():
    bot = build_bot("123456:TEST-TOKEN")
    assert len(bot.callback_query_handlers) >= 6


def test_register_handlers_is_single_source():
    """Регистрация живёт в одном месте — main.py и web_app.py её переиспользуют."""
    bot = register_handlers(telebot.TeleBot("123456:TEST-TOKEN", threaded=False))
    assert bot.message_handlers and bot.callback_query_handlers


def test_is_configured_false_for_placeholder(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    assert config.is_configured() is False


def test_is_configured_true_for_real_token(monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", "123456:ABC")
    assert config.is_configured() is True


def test_webhook_url_stripped(monkeypatch):
    assert not config.WEBHOOK_URL.endswith("/")


def _update(text=None, data=None, update_id=1):
    """Собирает Update как от Telegram: сообщение или callback."""
    if data is not None:
        return telebot.types.Update.de_json({
            "update_id": update_id,
            "callback_query": {
                "id": "cq1",
                "from": {"id": 1, "is_bot": False, "first_name": "T"},
                "chat_instance": "ci",
                "data": data,
                "message": {"message_id": 5, "date": 0,
                            "chat": {"id": 1, "type": "private"}, "text": "msg"},
            },
        })
    return telebot.types.Update.de_json({
        "update_id": update_id,
        "message": {"message_id": 1, "date": 0, "text": text,
                    "chat": {"id": 1, "type": "private"},
                    "from": {"id": 1, "is_bot": False, "first_name": "T"}},
    })


def test_dispatch_routes_messages_to_commands(monkeypatch):
    """Проверяет реальную маршрутизацию telebot, а не только наличие хендлеров."""
    import core.bot_core as core

    seen = []
    monkeypatch.setattr(core, "cmd_start", lambda m, b: seen.append("start"))
    monkeypatch.setattr(core, "cmd_help", lambda m, b: seen.append("help"))
    monkeypatch.setattr(core, "cmd_top", lambda m, b: seen.append("top"))
    monkeypatch.setattr(core, "cmd_count", lambda m, b: seen.append("count"))
    monkeypatch.setattr(core, "handle_text_check", lambda m, b: seen.append("text"))

    bot = core.build_bot("123456:TEST-TOKEN")
    for text in ("/start", "/help", "/top", "/count", "просто текст"):
        bot.process_new_updates([_update(text=text)])
    assert seen == ["start", "help", "top", "count", "text"]


def test_dispatch_routes_callbacks(monkeypatch):
    import core.bot_core as core

    seen = []
    for name in ("show_main_menu", "start_training", "show_stats",
                 "show_leaderboard", "handle_answer", "handle_legacy_answer"):
        monkeypatch.setattr(core, name, lambda c, b, _n=name: seen.append(_n))

    bot = core.build_bot("123456:TEST-TOKEN")
    for data in ("main_menu", "training_start", "stats", "leaderboard",
                 "a:12:0:1", "answer_слово"):
        bot.process_new_updates([_update(data=data)])
    assert seen == ["show_main_menu", "start_training", "show_stats",
                    "show_leaderboard", "handle_answer", "handle_legacy_answer"]


def test_commands_are_not_treated_as_text(monkeypatch):
    """Команда не должна попадать в текстовый обработчик-подсказку."""
    import core.bot_core as core

    seen = []
    monkeypatch.setattr(core, "cmd_start", lambda m, b: seen.append("start"))
    monkeypatch.setattr(core, "handle_text_check", lambda m, b: seen.append("text"))
    bot = core.build_bot("123456:TEST-TOKEN")
    bot.process_new_updates([_update(text="/start")])
    assert seen == ["start"]

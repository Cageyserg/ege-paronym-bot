"""Общие фикстуры тестов: in-memory MongoDB (mongomock), data_manager, фейковый бот."""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_manager import DataManager  # noqa: E402


class FakeBot:
    """Минимальная заглушка telebot.TeleBot, записывающая вызовы."""

    def __init__(self):
        self.calls = []
        self._message_id = 1000

    # ---- API ----
    def answer_callback_query(self, callback_id, text=None, show_alert=False):
        self.calls.append(("answer_callback_query", callback_id, text, show_alert))

    def edit_message_text(self, text, chat_id, message_id, reply_markup=None, parse_mode=None):
        self.calls.append(("edit_message_text", text, chat_id, message_id, reply_markup, parse_mode))

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.calls.append(("edit_message_reply_markup", chat_id, message_id, reply_markup))

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self._message_id += 1
        self.calls.append(("send_message", chat_id, text, reply_markup, parse_mode))
        return SimpleNamespace(message_id=self._message_id)

    def delete_message(self, chat_id, message_id):
        self.calls.append(("delete_message", chat_id, message_id))

    # ---- helpers ----
    def last(self, kind=None):
        for call in reversed(self.calls):
            if kind is None or call[0] == kind:
                return call
        return None

    def count(self, kind):
        return sum(1 for call in self.calls if call[0] == kind)


@pytest.fixture
def fake_bot():
    return FakeBot()


@pytest.fixture
def mongo_client():
    """Изолированный in-memory MongoDB на каждый тест."""
    import mongomock

    return mongomock.MongoClient()


@pytest.fixture
def storage(mongo_client):
    """MongoDatabase поверх mongomock — реальные запросы, без сети."""
    from utils.mongo_database import MongoDatabase

    return MongoDatabase(client=mongo_client, db_name="test_db")


@pytest.fixture
def manager(storage):
    """DataManager с подключённым MongoDB-хранилищем."""
    dm = DataManager(storage=storage)
    yield dm


@pytest.fixture
def callbacks(manager, monkeypatch):
    """Модуль handlers.callbacks с подменённым data_manager и чистым состоянием."""
    from handlers import callbacks as cb

    monkeypatch.setattr(cb, "data_manager", manager)
    monkeypatch.setattr(cb, "quiz", cb.QuizStore(max_users=100))
    monkeypatch.setattr(cb, "leaderboard_message_ids", cb.BoundedDict(maxsize=10))
    return cb


@pytest.fixture
def user():
    return SimpleNamespace(id=42, username="tester", first_name="Тест")


@pytest.fixture
def message():
    return SimpleNamespace(chat=SimpleNamespace(id=42), message_id=7, chat_id=42)


def make_call(user, message, data, call_id="cb-1"):
    """Фабрика callback-объекта."""
    return SimpleNamespace(id=call_id, data=data, from_user=user, message=message)

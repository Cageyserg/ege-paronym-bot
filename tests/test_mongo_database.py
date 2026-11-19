"""Тесты MongoDB-хранилища: реальные запросы через mongomock, без сети."""

import pytest

from utils.mongo_database import COLLECTION_NAME, MongoDatabase, StorageUnavailable


def test_create_unique_index_on_user_id(storage):
    indexes = storage._col.index_information()
    assert indexes["user_id_1"]["key"] == [("user_id", 1)]
    assert indexes["user_id_1"].get("unique") is True


def test_get_user_stats_creates_zero_document(storage):
    row = storage.get_user_stats(1, "u", "Имя")
    assert row["user_id"] == 1
    assert row["correct_answers"] == 0
    assert row["total_answers"] == 0
    assert row["max_streak"] == 0
    assert row["username"] == "u"
    assert row["firstname"] == "Имя"
    assert "_id" not in row


def test_get_user_stats_is_idempotent(storage):
    storage.get_user_stats(1)
    storage.get_user_stats(1)
    assert storage._col.count_documents({"user_id": 1}) == 1


def test_correct_answer_increments_counters(storage):
    storage.record_answer(1, True, "u", "И")
    row = storage.record_answer(1, True, "u", "И")
    assert (row["correct_answers"], row["total_answers"], row["streak"]) == (2, 2, 2)
    assert row["max_streak"] == 2


def test_wrong_answer_resets_streak_keeps_max(storage):
    storage.record_answer(1, True)
    storage.record_answer(1, True)
    row = storage.record_answer(1, False)
    assert row["correct_answers"] == 2
    assert row["total_answers"] == 3
    assert row["streak"] == 0
    assert row["max_streak"] == 2


def test_max_streak_keeps_historical_best(storage):
    for _ in range(3):
        storage.record_answer(1, True)
    storage.record_answer(1, False)
    storage.record_answer(1, True)
    row = storage.get_user_stats(1)
    assert row["max_streak"] == 3
    assert row["streak"] == 1


def test_names_are_persisted_with_answer(storage):
    storage.record_answer(7, True, "nick", "Ник")
    raw = storage._col.find_one({"user_id": 7})
    assert raw["username"] == "nick"
    assert raw["firstname"] == "Ник"


def test_names_are_not_wiped_by_empty_values(storage):
    storage.record_answer(7, True, "nick", "Ник")
    storage.record_answer(7, True, None, None)
    raw = storage._col.find_one({"user_id": 7})
    assert raw["username"] == "nick"
    assert raw["firstname"] == "Ник"


def test_answer_for_unknown_user_upserts(storage):
    assert storage._col.count_documents({}) == 0
    storage.record_answer(99, True)
    assert storage._col.count_documents({"user_id": 99}) == 1


def test_leaderboard_sorted_by_correct_answers(storage):
    for _ in range(3):
        storage.record_answer(2, True)
    for _ in range(2):
        storage.record_answer(1, True)
    assert [r["user_id"] for r in storage.get_leaderboard(limit=5)] == [2, 1]


def test_leaderboard_tie_broken_by_max_streak(storage):
    """При равном числе верных ответов выше тот, у кого длиннее лучшая серия."""
    storage.record_answer(1, True)
    storage.record_answer(1, False)
    storage.record_answer(1, True)
    storage.record_answer(2, True)
    storage.record_answer(2, True)
    storage.record_answer(2, False)
    board = storage.get_leaderboard(limit=5)
    rows = {r["user_id"]: r for r in board}
    assert rows[2]["correct_answers"] == rows[1]["correct_answers"] == 2
    assert rows[2]["max_streak"] > rows[1]["max_streak"]
    assert [r["user_id"] for r in board] == [2, 1]


def test_leaderboard_excludes_zero_correct(storage):
    storage.record_answer(1, False)
    storage.record_answer(2, True)
    assert [r["user_id"] for r in storage.get_leaderboard(limit=10)] == [2]


def test_leaderboard_respects_limit(storage):
    for uid in range(1, 6):
        storage.record_answer(uid, True)
    assert len(storage.get_leaderboard(limit=2)) == 2


def test_reset_user_stats(storage):
    storage.record_answer(1, True, "u", "И")
    storage.reset_user_stats(1)
    row = storage.get_user_stats(1)
    assert (row["correct_answers"], row["total_answers"], row["max_streak"]) == (0, 0, 0)
    assert row["username"] == "u"  # ник не теряется


def test_all_user_stats_returns_everyone(storage):
    storage.record_answer(1, True)
    storage.record_answer(2, False)
    assert {r["user_id"] for r in storage.get_all_user_stats()} == {1, 2}


def test_requires_uri(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    with pytest.raises(StorageUnavailable, match="MONGODB_URI"):
        MongoDatabase(None)


def test_collection_name_is_user_stats():
    assert COLLECTION_NAME == "user_stats"


def test_leaderboard_index_exists(storage):
    """Сортировка лидерборда должна идти по индексу, а не по всей коллекции."""
    keys = [tuple(info["key"]) for info in storage._col.index_information().values()]
    assert (("correct_answers", -1), ("max_streak", -1)) in keys

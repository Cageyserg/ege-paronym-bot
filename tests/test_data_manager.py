"""Тесты модуля данных: загрузка заданий и статистика строго через MongoDB."""

import json

import pytest

from utils.data_manager import DataManager, accuracy


def test_load_tasks_filters_broken_entries(tmp_path):
    path = tmp_path / "paronyms.json"
    path.write_text(json.dumps([
        {"id": 1, "task": "a ___ b", "options": ["x", "y"], "correct_answer": "x"},
        {"id": 2, "task": "нет вариантов", "options": []},
        {"id": 3, "task": "нет ответа", "options": ["x"]},
    ]), encoding="utf-8")
    dm = DataManager(str(path))
    assert [t["id"] for t in dm.tasks] == [1]


def test_load_tasks_missing_file_returns_empty(tmp_path):
    dm = DataManager(str(tmp_path / "nope.json"))
    assert dm.tasks == []
    assert dm.get_random_question() is None


def test_repo_data_is_valid():
    dm = DataManager()
    assert len(dm.tasks) > 300
    for task in dm.tasks:
        assert task["correct_answer"] in task["options"]
        assert len(task["options"]) >= 2


def test_get_random_question_shuffles_and_keeps_answer():
    dm = DataManager()
    for _ in range(20):
        q = dm.get_random_question()
        assert q["correct_answer"] in q["options"]
        assert set(q) >= {"id", "task", "options", "correct_answer", "explanation"}


def test_stats_counts_correct_and_total(manager):
    manager.update_user_stats(1, True, "u", "Имя")
    manager.update_user_stats(1, False, "u", "Имя")
    stats = manager.get_user_stats(1)
    assert stats["correct_answers"] == 1
    assert stats["total_answers"] == 2
    assert stats["streak"] == 0
    assert stats["max_streak"] == 1


def test_accuracy_helper():
    assert accuracy(0, 0) == 0.0
    assert accuracy(1, 2) == 50.0
    assert accuracy(2, 3) == 66.7


def test_stats_persist_in_mongo_not_in_ram(manager, storage):
    """После записи данные лежат в MongoDB и видны из второго DataManager."""
    manager.update_user_stats(5, True, "vasya", "Вася")

    raw = storage._col.find_one({"user_id": 5})
    assert (raw["correct_answers"], raw["total_answers"]) == (1, 1)
    assert raw["username"] == "vasya"
    assert raw["firstname"] == "Вася"

    fresh = DataManager(storage=storage)
    stats = fresh.get_user_stats(5)
    assert stats["correct_answers"] == 1
    assert stats["username"] == "vasya"


def test_wrong_answer_updates_mongo(manager, storage):
    manager.update_user_stats(6, True, "u", "")
    manager.update_user_stats(6, False, "u", "")
    raw = storage._col.find_one({"user_id": 6})
    assert raw["total_answers"] == 2
    assert raw["correct_answers"] == 1
    assert raw["streak"] == 0
    assert raw["max_streak"] == 1


def test_stats_without_storage_raises():
    dm = DataManager()
    with pytest.raises(RuntimeError):
        dm.get_user_stats(1)


def test_leaderboard_sorted_and_limited(manager):
    for uid, correct in [(1, 3), (2, 5), (3, 0)]:
        for _ in range(correct):
            manager.update_user_stats(uid, True, f"u{uid}", "")
    rows = manager.get_leaderboard(limit=2)
    assert [r["user_id"] for r in rows] == [2, 1]
    assert rows[0]["rank"] == 1
    assert rows[0]["percentage"] == 100.0
    assert all(r["correct_answers"] > 0 for r in rows)


def test_leaderboard_percentage_uses_total(manager):
    manager.update_user_stats(1, True, "u", "")
    manager.update_user_stats(1, False, "u", "")
    entry = manager.get_leaderboard(limit=1)[0]
    assert entry["percentage"] == 50.0
    assert entry["total_answers"] == 2


def test_reset_user_stats(manager):
    manager.update_user_stats(1, True, "u", "")
    manager.reset_user_stats(1)
    stats = manager.get_user_stats(1)
    assert stats["correct_answers"] == 0
    assert stats["total_answers"] == 0
    assert stats["max_streak"] == 0


@pytest.mark.parametrize("firstname,username,expected_first", [
    ("Иван", "ivan", "Иван"),
    ("", "ivan", ""),
])
def test_get_user_stats_updates_names(manager, firstname, username, expected_first):
    manager.update_user_stats(3, False, username, firstname)
    stats = manager.get_user_stats(3)
    assert stats["username"] == username
    assert stats["firstname"] == expected_first


def test_no_sqlite_module_left():
    """SQLite-слой удалён: единственное хранилище — MongoDB."""
    import importlib.util

    assert importlib.util.find_spec("utils.database") is None


def test_stats_are_written_straight_to_mongo(manager, storage):
    """Между ответом и MongoDB нет промежуточного кэша."""
    manager.update_user_stats(11, True, "u", "")
    assert storage._col.count_documents({"user_id": 11}) == 1
    manager.update_user_stats(11, True, "u", "")
    assert storage._col.find_one({"user_id": 11})["correct_answers"] == 2


def test_no_sqlite_module_anymore():
    """SQLite-слой удалён: единственное хранилище — MongoDB."""
    import importlib.util

    assert importlib.util.find_spec("utils.database") is None


def test_writes_go_straight_to_mongo(manager, storage):
    """Между ответом и MongoDB нет промежуточного кэша или файла."""
    manager.update_user_stats(11, True, "u", "")
    assert storage._col.count_documents({"user_id": 11}) == 1
    manager.update_user_stats(11, True, "u", "")
    assert storage._col.find_one({"user_id": 11})["correct_answers"] == 2

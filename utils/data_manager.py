"""
Данные бота: задания из paronyms.json и доступ к статистике.

Статистика НЕ кэшируется и НЕ дублируется в памяти или SQLite: единственный
источник правды — MongoDB (utils/mongo_database.py). DataManager только
загружает задания и делегирует операции со статистикой в хранилище.
"""

import json
import logging
import os
import random
from typing import Any

from utils.formatting import display_name

logger = logging.getLogger(__name__)

# Путь к файлу заданий относительно корня проекта.
DEFAULT_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paronyms.json"
)


def accuracy(correct: int, total: int) -> float:
    """Точность в процентах; 0.0 при отсутствии ответов."""
    if not total:
        return 0.0
    return round(correct * 100.0 / total, 1)


class DataManager:
    """Задания из paronyms.json + операции статистики через MongoDB."""

    def __init__(self, data_path: str | None = None, storage=None):
        self._storage = storage
        self.tasks = self._load_tasks(data_path or DEFAULT_DATA_FILE)
        logger.info("DataManager: загружено %d заданий", len(self.tasks))

    # ==================== ХРАНИЛИЩЕ ====================

    @property
    def storage(self):
        """MongoDB-хранилище статистики. Без него операции со статистикой падают."""
        if self._storage is None:
            raise RuntimeError(
                "Хранилище статистики не подключено: вызовите init_data_manager(storage)."
            )
        return self._storage

    def attach_storage(self, storage):
        self._storage = storage
        return self

    # ==================== ЗАДАНИЯ ====================

    @staticmethod
    def _load_tasks(path: str) -> list[dict]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Ошибка загрузки заданий из %s: %s", path, e)
            return []
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return [t for t in tasks if t.get("options") and t.get("correct_answer")]

    def get_random_question(self) -> dict[str, Any] | None:
        """Случайное задание с перемешанными вариантами ответа."""
        if not self.tasks:
            return None
        task = random.choice(self.tasks)
        options = list(task["options"])
        random.shuffle(options)
        return {
            "id": task["id"],
            "task": task.get("task") or task.get("question", ""),
            "options": options,
            "correct_answer": task["correct_answer"],
            "explanation": task.get("explanation", ""),
            "word": task.get("word", ""),
        }

    # ==================== СТАТИСТИКА (только MongoDB) ====================

    def get_user_stats(self, user_id: int, username: str | None = None,
                       firstname: str | None = None) -> dict[str, Any]:
        """Читает статистику из MongoDB, попутно сохраняя актуальные ник и имя."""
        return self.storage.get_user_stats(user_id, username, firstname)

    def update_user_stats(self, user_id: int, is_correct: bool,
                          username: str | None = None,
                          firstname: str | None = None) -> dict[str, Any]:
        """Записывает ответ в MongoDB атомарно и возвращает новую статистику."""
        return self.storage.record_answer(user_id, is_correct, username, firstname)

    def get_leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        """Топ из MongoDB с рангом, отображаемым именем и точностью."""
        rows = self.storage.get_leaderboard(limit)
        return [
            {
                "rank": idx + 1,
                "user_id": row.get("user_id"),
                "username": row.get("username") or "",
                "firstname": row.get("firstname") or "",
                "display_name": display_name(row),
                "correct_answers": row.get("correct_answers", 0),
                "total_answers": row.get("total_answers", 0),
                "percentage": accuracy(row.get("correct_answers", 0),
                                       row.get("total_answers", 0)),
                "max_streak": row.get("max_streak", 0),
            }
            for idx, row in enumerate(rows)
        ]

    def reset_user_stats(self, user_id: int) -> None:
        self.storage.reset_user_stats(user_id)


# Модульный экземпляр: задания читаются один раз при импорте.
data_manager = DataManager()


def init_data_manager(storage, manager: DataManager | None = None) -> DataManager:
    """
    Подключает хранилище статистики к DataManager.

    manager позволяет подменить экземпляр в тестах, не трогая модульный.
    """
    target = manager or data_manager
    target.attach_storage(storage)
    logger.info("DataManager инициализирован: статистика в MongoDB")
    return target

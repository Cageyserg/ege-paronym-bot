"""
MongoDB — единственное хранилище статистики пользователей.

Здесь и только здесь лежат: количество верно решённых слов, текущая серия,
максимальная серия, username и имя пользователя. Локального кэша и SQLite нет:
каждый ответ пишется в MongoDB атомарным апдейтом, поэтому данные не
расходятся между процессами и не теряются при рестарте.

Документ коллекции user_stats:
    user_id          int    — Telegram id (уникальный индекс)
    username         str    — @username, если есть
    firstname        str    — имя из профиля
    correct_answers  int    — сколько слов решено верно
    streak           int    — текущая серия верных подряд
    max_streak       int    — максимальная серия верных подряд
"""

import logging
import os
from typing import Any

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "ege_paronym_bot"
COLLECTION_NAME = "user_stats"

# Поля, которые отдаются наружу (без служебного _id).
PUBLIC_FIELDS = {
    "_id": 0,
    "user_id": 1,
    "username": 1,
    "firstname": 1,
    "correct_answers": 1,
    "streak": 1,
    "max_streak": 1,
}

_EMPTY_COUNTERS = {
    "correct_answers": 0,
    "streak": 0,
    "max_streak": 0,
}


class StorageUnavailable(RuntimeError):
    """MongoDB недоступна или не сконфигурирована."""


class MongoDatabase:
    """Атомарные операции над статистикой пользователей в MongoDB."""

    def __init__(self, uri: str | None = None, db_name: str | None = None,
                 client: MongoClient | None = None):
        """
        client передаётся только в тестах (mongomock); в бою соединение
        создаётся по MONGODB_URI.
        """
        if client is not None:
            self._client = client
        else:
            uri = uri or os.getenv("MONGODB_URI")
            if not uri:
                raise StorageUnavailable(
                    "MONGODB_URI не задан: статистика хранится только в MongoDB, "
                    "поэтому без него бот работать не может."
                )
            self._client = MongoClient(uri, serverSelectionTimeoutMS=8000)
            try:
                self._client.admin.command("ping")
            except PyMongoError as e:
                raise StorageUnavailable(f"Не удалось подключиться к MongoDB: {e}") from e

        self._db_name = db_name or os.getenv("MONGODB_DB") or DEFAULT_DB_NAME
        self._col = self._client[self._db_name][COLLECTION_NAME]
        self._col.create_index("user_id", unique=True)
        # Индекс под сортировку таблицы лидеров (correct_answers, затем max_streak).
        self._col.create_index([("correct_answers", -1), ("max_streak", -1)])
        logger.info("MongoDB: коллекция %s.%s готова", self._db_name, COLLECTION_NAME)

    def close(self):
        if self._client is not None:
            self._client.close()

    # ==================== ЗАПИСЬ ====================

    def record_answer(self, user_id: int, is_correct: bool,
                      username: str | None = None,
                      firstname: str | None = None) -> dict[str, Any]:
        """
        Учитывает один ответ атомарно и возвращает актуальный документ.

        Агрегационный пайплайн выполняет инкременты и обновление max_streak
        на стороне MongoDB, поэтому гонки между процессами невозможны.

        Хранятся только три счётчика: верно решённые слова, текущая серия и
        максимальная серия. Отдельного «всего ответов» нет — неверный ответ
        лишь обнуляет текущую серию.
        """
        if is_correct:
            pipeline = [
                {"$set": {
                    "correct_answers": {"$add": [{"$ifNull": ["$correct_answers", 0]}, 1]},
                    "streak": {"$add": [{"$ifNull": ["$streak", 0]}, 1]},
                }},
                {"$set": {"max_streak": {"$max": [{"$ifNull": ["$max_streak", 0]},
                                                  "$streak"]}}},
            ]
        else:
            pipeline = [{"$set": {"streak": 0}}]

        # Ник и имя обновляем в том же апдейте, чтобы они всегда были свежими.
        names = {}
        if username:
            names["username"] = username
        if firstname:
            names["firstname"] = firstname
        if names:
            pipeline.append({"$set": names})

        return self._update_one(user_id, pipeline)

    def get_user_stats(self, user_id: int, username: str | None = None,
                       firstname: str | None = None) -> dict[str, Any]:
        """
        Статистика пользователя; при первом обращении создаёт нулевой документ.

        Ник и имя тоже сохраняются здесь — другого места для них нет.
        """
        on_insert = {"user_id": user_id, **_EMPTY_COUNTERS}
        names = {}
        if username:
            names["username"] = username
        if firstname:
            names["firstname"] = firstname

        update: dict[str, Any] = {"$setOnInsert": on_insert}
        if names:
            update["$set"] = names

        doc = self._col.find_one_and_update(
            {"user_id": user_id}, update,
            upsert=True, return_document=ReturnDocument.AFTER,
            projection=PUBLIC_FIELDS,
        )
        return self._normalize(doc)

    def reset_user_stats(self, user_id: int) -> None:
        self._col.update_one({"user_id": user_id}, {"$set": dict(_EMPTY_COUNTERS)})

    # ==================== ЧТЕНИЕ ====================

    def get_leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        """Топ по верным ответам; ничьи разрешаются по лучшей серии."""
        cursor = (
            self._col.find({"correct_answers": {"$gt": 0}}, PUBLIC_FIELDS)
            .sort([("correct_answers", -1), ("max_streak", -1)])
            .limit(limit)
        )
        return [self._normalize(doc) for doc in cursor]

    def get_all_user_stats(self) -> list[dict[str, Any]]:
        return [self._normalize(doc) for doc in self._col.find({}, PUBLIC_FIELDS)]

    # ==================== ВНУТРЕННЕЕ ====================

    def _update_one(self, user_id: int, pipeline: list[dict]) -> dict[str, Any]:
        try:
            doc = self._col.find_one_and_update(
                {"user_id": user_id}, pipeline,
                upsert=True, return_document=ReturnDocument.AFTER,
                projection=PUBLIC_FIELDS,
            )
        except PyMongoError as e:
            logger.error("MongoDB: ошибка записи статистики user_id=%s: %s", user_id, e)
            raise StorageUnavailable(f"Не удалось записать статистику: {e}") from e
        return self._normalize(doc)

    @staticmethod
    def _normalize(doc: dict[str, Any] | None) -> dict[str, Any]:
        """Достраивает отсутствующие счётчики нулями и убирает _id."""
        result = {k: v for k, v in (doc or {}).items() if k != "_id"}
        for key, default in _EMPTY_COUNTERS.items():
            result.setdefault(key, default)
        result.setdefault("username", "")
        result.setdefault("firstname", "")
        return result

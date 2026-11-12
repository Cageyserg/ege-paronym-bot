"""
MongoDB-бэкенд для StatsCache. Интерфейс совместим с utils.database.Database.
Используется на Render (эфемерная ФС). Локально — SQLite.
"""
import os
import logging
from typing import Any, Dict, List, Optional
from pymongo import MongoClient, UpdateOne

logger = logging.getLogger(__name__)

DB_NAME = "ege_paronym_bot"
COLLECTION_NAME = "user_stats"


class MongoDatabase:
    def __init__(self, uri: Optional[str] = None, db_name: str = DB_NAME):
        uri = uri or os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI не задан")
        self._client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        self._col = self._client[db_name][COLLECTION_NAME]
        self._client.admin.command("ping")
        self._col.create_index("user_id", unique=True)
        logger.info("MongoDatabase: подключение OK, %s.%s", db_name, COLLECTION_NAME)

    def get_all_user_stats(self) -> List[Dict[str, Any]]:
        return list(self._col.find({}, {"_id": 0}))

    def batch_update_user_stats(self, rows: List[tuple]) -> None:
        if not rows:
            return
        ops = [
            UpdateOne(
                {"user_id": r[0]},
                {"$set": {
                    "user_id": r[0], "username": r[1], "firstname": r[2],
                    "correct_answers": r[3], "streak": r[4], "max_streak": r[5],
                }},
                upsert=True,
            )
            for r in rows
        ]
        self._col.bulk_write(ops, ordered=False)

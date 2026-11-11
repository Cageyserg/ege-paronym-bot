"""
Модуль для работы с базой данных SQLite.

Используется ТОЛЬКО для персистентной статистики пользователей.
Вопросы/ответы хранятся в paronyms.json и не затрагиваются БД.
Таблицы questions, answers, user_solved_words удалены — они избыточны.

Безопасность потоков: каждое соединение создаётся внутри метода.
PRAGMA journal_mode=WAL для конкурентного чтения/записи.
"""

import sqlite3
import os
from typing import Dict, List, Any


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(_BASE_DIR, "data", "bot_database.db")


class Database:
    """Лёгкий SQLite-обёртка: только user_stats таблица."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._init_db()

    # ==================== CONNECTION FACTORY ====================

    def _get_connection(self):
        """Создаёт новое соединение при каждом вызове. Безопасно для многопоточности."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==================== INIT ====================

    def _init_db(self):
        """Создаёт таблицу user_stats и устанавливает WAL-режим."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Включаем WAL для конкурентного чтения/записи без блокировок.
            # synchronous=NORMAL — достаточно безопасно + быстрее.
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    firstname TEXT,
                    correct_answers INTEGER DEFAULT 0,
                    streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    # ==================== READ ====================

    def get_user_stats(self, user_id: int, username: str = None, firstname: str = None) -> Dict[str, Any]:
        """Возвращает статистику пользователя. Создаёт запись при первом обращении."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    "INSERT INTO user_stats (user_id, username, firstname) VALUES (?, ?, ?)",
                    (user_id, username or "Anonymous", firstname or "")
                )
                conn.commit()
                return {
                    "username": username or "Anonymous",
                    "firstname": firstname or "",
                    "correct_answers": 0,
                    "streak": 0,
                    "max_streak": 0,
                }

            return {
                "username": row["username"] or "Anonymous",
                "firstname": row["firstname"] or "",
                "correct_answers": row["correct_answers"],
                "streak": row["streak"],
                "max_streak": row["max_streak"],
            }

    def get_all_user_stats(self) -> List[Dict[str, Any]]:
        """Возвращает ВСЕХ пользователей — для загрузки кэша при старте."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_stats ORDER BY correct_answers DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, firstname, correct_answers, streak, max_streak
                FROM user_stats
                WHERE correct_answers > 0
                ORDER BY correct_answers DESC
                LIMIT ?
            """, (limit,))

            result = []
            for idx, row in enumerate(cursor.fetchall(), 1):
                result.append({
                    "rank": idx,
                    "user_id": row["user_id"],
                    "username": row["username"] or f"User {row['user_id']}",
                    "firstname": row["firstname"] or "",
                    "correct_answers": row["correct_answers"],
                    "total_answers": row["correct_answers"],
                    "percentage": 100.0,
                    "max_streak": row["max_streak"],
                })
            return result

    # ==================== WRITE (batch) ====================

    def batch_update_user_stats(self, rows: List[tuple]):
        """
        Батч-запись пользователей в одну транзакцию одним executemany.
        
        Каждый кортеж: (user_id, username, firstname, correct_answers, streak, max_streak)
        """
        if not rows:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO user_stats (user_id, username, firstname, correct_answers, streak, max_streak)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    firstname = excluded.firstname,
                    correct_answers = excluded.correct_answers,
                    streak = excluded.streak,
                    max_streak = excluded.max_streak
            """, rows)
            conn.commit()

    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя (для обратной совместимости)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_stats SET correct_answers = 0, streak = 0, max_streak = 0
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    # ==================== DEPRECATED ====================

    def get_random_question(self):
        """Удалено — вопросы из paronyms.json."""
        return None

    def update_user_stats(self, *args, **kwargs):
        """Удалено — используйте StatsCache.update_user_stats()."""
        pass

    def get_user_solved_words_count(self, user_id: int) -> int:
        """Удалено — таблица user_solved_words не нужна."""
        return 0

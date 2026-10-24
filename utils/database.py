"""
Модуль для работы с базой данных SQLite.
"""

import sqlite3
import json
import os
import random
from typing import Dict, List, Any, Optional
from config import QUESTIONS_FILE, ANSWERS_FILE


class Database:
    """Класс для управления базой данных SQLite."""
    
    def __init__(self, db_path: str = "data/bot_database.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._load_data_from_json()
    
    def _get_connection(self):
        """Создаёт соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Инициализирует таблицы базы данных."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица вопросов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY,
                    sentence TEXT NOT NULL,
                    explanation TEXT NOT NULL
                )
            """)
            
            # Таблица ответов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY,
                    question_id INTEGER NOT NULL,
                    correct TEXT NOT NULL,
                    wrong TEXT NOT NULL,
                    FOREIGN KEY (question_id) REFERENCES questions(id)
                )
            """)
            
            # Таблица статистики пользователей
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
            
            # Таблица решённых слов пользователя
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_solved_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, question_id, word),
                    FOREIGN KEY (user_id) REFERENCES user_stats(user_id),
                    FOREIGN KEY (question_id) REFERENCES questions(id)
                )
            """)
            
            conn.commit()
    
    def _load_data_from_json(self):
        """Загружает вопросы и ответы из JSON файлов."""
        # Проверяем, есть ли уже данные
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM questions")
            if cursor.fetchone()[0] > 0:
                return  # Данные уже загружены
        
        # Загружаем вопросы
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
            
            for q in questions_data.get("questions", []):
                cursor.execute("""
                    INSERT OR IGNORE INTO questions (id, sentence, explanation)
                    VALUES (?, ?, ?)
                """, (q["id"], q["sentence"], q["explanation"]))
        
        # Загружаем ответы
        if os.path.exists(ANSWERS_FILE):
            with open(ANSWERS_FILE, 'r', encoding='utf-8') as f:
                answers_data = json.load(f)
            
            for a in answers_data.get("answers", []):
                cursor.execute("""
                    INSERT OR IGNORE INTO answers (question_id, correct, wrong)
                    VALUES (?, ?, ?)
                """, (a["question_id"], a["correct"], json.dumps(a["wrong"])))
        
        conn.commit()
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос с перемешанными вариантами ответов."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем случайный вопрос
            cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1")
            question_row = cursor.fetchone()
            
            if not question_row:
                return None
            
            # Получаем ответы для этого вопроса
            cursor.execute("SELECT correct, wrong FROM answers WHERE question_id = ?", (question_row["id"],))
            answer_row = cursor.fetchone()
            
            if not answer_row:
                return None
            
            # Формируем список вариантов: правильный + неправильные
            wrong_list = json.loads(answer_row["wrong"])
            all_words = [answer_row["correct"]] + wrong_list
            
            # Перемешиваем варианты
            random.shuffle(all_words)
            
            return {
                "question_id": question_row["id"],
                "sentence": question_row["sentence"],
                "explanation": question_row["explanation"],
                "correct": answer_row["correct"],
                "words": all_words
            }
    
    def get_user_stats(self, user_id: int, username: str = None, firstname: str = None) -> Dict[str, int]:
        """Возвращает статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                cursor.execute("""
                    INSERT INTO user_stats (user_id, username, firstname)
                    VALUES (?, ?, ?)
                """, (user_id, username or "Anonymous", firstname or ""))
                conn.commit()
                return {
                    "username": username or "Anonymous",
                    "firstname": firstname or "",
                    "correct_answers": 0,
                    "streak": 0,
                    "max_streak": 0
                }
            
            if username and row["username"] != username:
                cursor.execute(
                    "UPDATE user_stats SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
                conn.commit()
            
            if firstname and row["firstname"] != firstname:
                cursor.execute(
                    "UPDATE user_stats SET firstname = ? WHERE user_id = ?",
                    (firstname, user_id)
                )
                conn.commit()
            
            return {
                "username": row["username"] or "Anonymous",
                "firstname": row["firstname"] or "",
                "correct_answers": row["correct_answers"],
                "streak": row["streak"],
                "max_streak": row["max_streak"]
            }
    
    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None, firstname: str = None, question_id: int = None, word: str = None):
        """Обновляет статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if is_correct:
                stats = cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
                new_streak = (stats["streak"] if stats else 0) + 1
                new_max_streak = max(stats["max_streak"] if stats else 0, new_streak)

                cursor.execute("""
                    UPDATE user_stats
                    SET correct_answers = correct_answers + 1,
                        streak = ?,
                        max_streak = ?
                    WHERE user_id = ?
                """, (new_streak, new_max_streak, user_id))

                if question_id and word:
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_solved_words (user_id, question_id, word)
                        VALUES (?, ?, ?)
                    """, (user_id, question_id, word))
            else:
                cursor.execute("""
                    UPDATE user_stats
                    SET streak = 0
                    WHERE user_id = ?
                """, (user_id,))

            if username:
                cursor.execute(
                    "UPDATE user_stats SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )

            if firstname:
                cursor.execute(
                    "UPDATE user_stats SET firstname = ? WHERE user_id = ?",
                    (firstname, user_id)
                )

            conn.commit()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, correct_answers
                FROM user_stats
                WHERE correct_answers > 0
                ORDER BY correct_answers DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            result = []
            for idx, row in enumerate(rows, 1):
                result.append({
                    "rank": idx,
                    "user_id": row["user_id"],
                    "username": row["username"] or f"User {row['user_id']}",
                    "correct_answers": row["correct_answers"],
                    "total_answers": row["correct_answers"],
                    "percentage": 100.0,
                    "max_streak": 0
                })
            return result
    
    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_stats
                SET correct_answers = 0,
                    streak = 0,
                    max_streak = 0
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
    
    def get_user_solved_words_count(self, user_id: int) -> int:
        """Возвращает количество уникальных решённых слов пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT word) FROM user_solved_words WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

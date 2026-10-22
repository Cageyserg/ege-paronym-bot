"""
Модуль для работы с базой данных SQLite.
Заменяет JSON-файлы для более надёжного хранения данных и реализации таблицы лидеров.
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from config import DATA_FILE, STATS_FILE


class Database:
    """Класс для управления базой данных SQLite."""
    
    def __init__(self, db_path: str = "data/bot_database.db"):
        self.db_path = db_path
        # Создаём директорию, если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._load_paronyms_from_json()
    
    def _get_connection(self):
        """Создаёт соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Инициализирует таблицы базы данных."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица паронимов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paronyms (
                    id INTEGER PRIMARY KEY,
                    word1 TEXT NOT NULL,
                    word2 TEXT NOT NULL,
                    definition1 TEXT NOT NULL,
                    definition2 TEXT NOT NULL,
                    example1 TEXT NOT NULL,
                    example2 TEXT NOT NULL,
                    UNIQUE(word1, word2)
                )
            """)
            
            # Таблица тестовых вопросов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paronym_id INTEGER NOT NULL,
                    sentence TEXT NOT NULL,
                    correct_word TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    FOREIGN KEY (paronym_id) REFERENCES paronyms(id)
                )
            """)
            
            # Таблица статистики пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    total_answers INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    incorrect_answers INTEGER DEFAULT 0,
                    streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0
                )
            """)
            
            # Таблица решённых слов пользователя
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_solved_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    paronym_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, paronym_id, word),
                    FOREIGN KEY (user_id) REFERENCES user_stats(user_id),
                    FOREIGN KEY (paronym_id) REFERENCES paronyms(id)
                )
            """)
            
            conn.commit()
    
    def _load_paronyms_from_json(self):
        """Загружает паронимы из JSON файла в базу данных."""
        if not os.path.exists(DATA_FILE):
            return
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for paronym in data.get("paronyms", []):
                words = paronym["words"]
                definitions = paronym["definitions"]
                examples = paronym["examples"]
                
                # Вставляем или обновляем пару паронимов
                cursor.execute("""
                    INSERT OR REPLACE INTO paronyms 
                    (id, word1, word2, definition1, definition2, example1, example2)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    paronym["id"],
                    words[0], words[1],
                    definitions[words[0]], definitions[words[1]],
                    examples[words[0]], examples[words[1]]
                ))
                
                # Вставляем тестовые вопросы
                for question in paronym["test_questions"]:
                    cursor.execute("""
                        INSERT INTO test_questions 
                        (paronym_id, sentence, correct_word, explanation)
                        VALUES (?, ?, ?, ?)
                    """, (
                        paronym["id"],
                        question["sentence"],
                        question["correct"],
                        question["explanation"]
                    ))
            
            conn.commit()
    
    def get_all_paronyms(self) -> List[Dict[str, Any]]:
        """Возвращает список всех паронимов."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM paronyms")
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "words": [row["word1"], row["word2"]],
                    "definitions": {
                        row["word1"]: row["definition1"],
                        row["word2"]: row["definition2"]
                    },
                    "examples": {
                        row["word1"]: row["example1"],
                        row["word2"]: row["example2"]
                    }
                })
            return result
    
    def get_paronym_by_id(self, paronym_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает данные паронима по его ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM paronyms WHERE id = ?", (paronym_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "words": [row["word1"], row["word2"]],
                "definitions": {
                    row["word1"]: row["definition1"],
                    row["word2"]: row["definition2"]
                },
                "examples": {
                    row["word1"]: row["example1"],
                    row["word2"]: row["example2"]
                }
            }
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос из базы."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, q.sentence, q.correct_word, q.explanation
                FROM test_questions q
                JOIN paronyms p ON q.paronym_id = p.id
                ORDER BY RANDOM()
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "paronym_id": row["id"],
                "words": [row["word1"], row["word2"]],
                "sentence": row["sentence"],
                "correct": row["correct_word"],
                "explanation": row["explanation"],
                "definitions": {
                    row["word1"]: row["definition1"],
                    row["word2"]: row["definition2"]
                }
            }
    
    def find_paronym_in_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Ищет пароним в тексте и возвращает правильный вариант с объяснением."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM paronyms")
            rows = cursor.fetchall()
            
            for row in rows:
                word1, word2 = row["word1"], row["word2"]
                
                # Проверяем, есть ли слово1 или слово2 в тексте
                if word1.lower() in text.lower() or word2.lower() in text.lower():
                    # Простая эвристика: возвращаем первую найденную пару
                    # В реальном боте нужен более сложный анализ контекста
                    return {
                        "words": [word1, word2],
                        "definitions": {
                            word1: row["definition1"],
                            word2: row["definition2"]
                        },
                        "examples": {
                            word1: row["example1"],
                            word2: row["example2"]
                        }
                    }
            
            return None
    
    def get_user_stats(self, user_id: int, username: str = None) -> Dict[str, int]:
        """Возвращает статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                # Создаём запись для нового пользователя
                cursor.execute("""
                    INSERT INTO user_stats (user_id, username)
                    VALUES (?, ?)
                """, (user_id, username or "Anonymous"))
                conn.commit()
                return {
                    "total_answers": 0,
                    "correct_answers": 0,
                    "incorrect_answers": 0,
                    "streak": 0,
                    "max_streak": 0
                }
            
            # Обновляем username, если он изменился
            if username and row["username"] != username:
                cursor.execute(
                    "UPDATE user_stats SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
                conn.commit()
            
            return {
                "total_answers": row["total_answers"],
                "correct_answers": row["correct_answers"],
                "incorrect_answers": row["incorrect_answers"],
                "streak": row["streak"],
                "max_streak": row["max_streak"]
            }
    
    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None, paronym_id: int = None, word: str = None):
        """Обновляет статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if is_correct:
                cursor.execute("""
                    UPDATE user_stats 
                    SET total_answers = total_answers + 1,
                        correct_answers = correct_answers + 1,
                        streak = streak + 1,
                        max_streak = MAX(max_streak, streak + 1)
                    WHERE user_id = ?
                """, (user_id,))
                
                # Добавляем решённое слово
                if paronym_id and word:
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_solved_words (user_id, paronym_id, word)
                        VALUES (?, ?, ?)
                    """, (user_id, paronym_id, word))
            else:
                cursor.execute("""
                    UPDATE user_stats 
                    SET total_answers = total_answers + 1,
                        incorrect_answers = incorrect_answers + 1,
                        streak = 0
                    WHERE user_id = ?
                """, (user_id,))
            
            if username:
                cursor.execute(
                    "UPDATE user_stats SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
            
            conn.commit()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, correct_answers, total_answers, max_streak
                FROM user_stats
                WHERE total_answers > 0
                ORDER BY correct_answers DESC, max_streak DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            result = []
            for idx, row in enumerate(rows, 1):
                percentage = round((row["correct_answers"] / row["total_answers"]) * 100, 1) if row["total_answers"] > 0 else 0
                result.append({
                    "rank": idx,
                    "user_id": row["user_id"],
                    "username": row["username"] or f"User {row['user_id']}",
                    "correct_answers": row["correct_answers"],
                    "total_answers": row["total_answers"],
                    "percentage": percentage,
                    "max_streak": row["max_streak"]
                })
            return result
    
    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_stats
                SET total_answers = 0,
                    correct_answers = 0,
                    incorrect_answers = 0,
                    streak = 0,
                    max_streak = 0
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
    
    def get_user_solved_words_count(self, user_id: int) -> int:
        """Возвращает количество уникальных решённых слов пользователя."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(DISTINCT word) FROM user_solved_words WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

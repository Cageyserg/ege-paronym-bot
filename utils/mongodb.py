"""
Модуль для работы с MongoDB.
Заменяет SQLite для постоянного хранения данных на Render.
"""

import os
from typing import Dict, List, Any, Optional
from pymongo import MongoClient, ASCENDING
from config import DATA_FILE
import json


class MongoDB:
    """Класс для управления базой данных MongoDB."""
    
    def __init__(self, mongo_uri: str = None):
        if mongo_uri is None:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client["ege_paronym_bot"]
        
        # Коллекции
        self.paronyms_collection = self.db["paronyms"]
        self.questions_collection = self.db["test_questions"]
        self.stats_collection = self.db["user_stats"]
        self.solved_words_collection = self.db["user_solved_words"]
        
        # Создаём индексы
        self._create_indexes()
        
        # Загружаем паронимы из JSON
        self._load_paronyms_from_json()
    
    def _create_indexes(self):
        """Создаёт индексы для оптимизации запросов."""
        # Индекс для уникальности пары слов
        self.paronyms_collection.create_index([("word1", 1), ("word2", 1)], unique=True)
        
        # Индекс для user_id в статистике
        self.stats_collection.create_index("user_id", unique=True)
        
        # Индекс для уникальности решённых слов
        self.solved_words_collection.create_index(
            [("user_id", 1), ("paronym_id", 1), ("word", 1)],
            unique=True
        )
    
    def _load_paronyms_from_json(self):
        """Загружает паронимы из JSON файла в MongoDB."""
        if not os.path.exists(DATA_FILE):
            return
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем, есть ли уже данные
        if self.paronyms_collection.count_documents({}) > 0:
            return
        
        for paronym in data.get("paronyms", []):
            words = paronym["words"]
            definitions = paronym["definitions"]
            examples = paronym["examples"]
            
            # Вставляем или обновляем пару паронимов
            self.paronyms_collection.update_one(
                {"word1": words[0], "word2": words[1]},
                {
                    "$set": {
                        "id": paronym["id"],
                        "word1": words[0],
                        "word2": words[1],
                        "definition1": definitions[words[0]],
                        "definition2": definitions[words[1]],
                        "example1": examples[words[0]],
                        "example2": examples[words[1]]
                    }
                },
                upsert=True
            )
            
            # Вставляем тестовые вопросы
            for question in paronym["test_questions"]:
                self.questions_collection.update_one(
                    {
                        "paronym_id": paronym["id"],
                        "sentence": question["sentence"]
                    },
                    {
                        "$set": {
                            "paronym_id": paronym["id"],
                            "sentence": question["sentence"],
                            "correct_word": question["correct"],
                            "explanation": question["explanation"]
                        }
                    },
                    upsert=True
                )
    
    def get_all_paronyms(self) -> List[Dict[str, Any]]:
        """Возвращает список всех паронимов."""
        paronyms = list(self.paronyms_collection.find())
        result = []
        for p in paronyms:
            result.append({
                "id": p["id"],
                "words": [p["word1"], p["word2"]],
                "definitions": {
                    p["word1"]: p["definition1"],
                    p["word2"]: p["definition2"]
                },
                "examples": {
                    p["word1"]: p["example1"],
                    p["word2"]: p["example2"]
                }
            })
        return result
    
    def get_paronym_by_id(self, paronym_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает данные паронима по его ID."""
        p = self.paronyms_collection.find_one({"id": paronym_id})
        if not p:
            return None
        
        return {
            "id": p["id"],
            "words": [p["word1"], p["word2"]],
            "definitions": {
                p["word1"]: p["definition1"],
                p["word2"]: p["definition2"]
            },
            "examples": {
                p["word1"]: p["example1"],
                p["word2"]: p["example2"]
            }
        }
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос из базы."""
        import random
        
        # Получаем случайный вопрос
        pipeline = [{"$sample": {"size": 1}}]
        questions = list(self.questions_collection.aggregate(pipeline))
        
        if not questions:
            return None
        
        question = questions[0]
        
        # Получаем связанный пароним
        paronym = self.paronyms_collection.find_one({"id": question["paronym_id"]})
        
        if not paronym:
            return None
        
        return {
            "paronym_id": question["paronym_id"],
            "words": [paronym["word1"], paronym["word2"]],
            "sentence": question["sentence"],
            "correct": question["correct_word"],
            "explanation": question["explanation"],
            "definitions": {
                paronym["word1"]: paronym["definition1"],
                paronym["word2"]: paronym["definition2"]
            }
        }
    
    def find_paronym_in_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Ищет пароним в тексте и возвращает правильный вариант с объяснением."""
        paronyms = list(self.paronyms_collection.find())
        
        for p in paronyms:
            word1, word2 = p["word1"], p["word2"]
            
            if word1.lower() in text.lower() or word2.lower() in text.lower():
                return {
                    "words": [word1, word2],
                    "definitions": {
                        word1: p["definition1"],
                        word2: p["definition2"]
                    },
                    "examples": {
                        word1: p["example1"],
                        word2: p["example2"]
                    }
                }
        
        return None
    
    def get_user_stats(self, user_id: int, username: str = None) -> Dict[str, int]:
        """Возвращает статистику пользователя."""
        stats = self.stats_collection.find_one({"user_id": user_id})
        
        if not stats:
            # Создаём запись для нового пользователя
            new_stats = {
                "user_id": user_id,
                "username": username or "Anonymous",
                "correct_answers": 0,
                "streak": 0,
                "max_streak": 0
            }
            self.stats_collection.insert_one(new_stats)
            return {
                "correct_answers": 0,
                "streak": 0,
                "max_streak": 0
            }
        
        # Обновляем username, если он изменился
        if username and stats.get("username") != username:
            self.stats_collection.update_one(
                {"user_id": user_id},
                {"$set": {"username": username}}
            )
        
        return {
            "correct_answers": stats.get("correct_answers", 0),
            "streak": stats.get("streak", 0),
            "max_streak": stats.get("max_streak", 0)
        }
    
    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None, paronym_id: int = None, word: str = None):
        """Обновляет статистику пользователя."""
        if is_correct:
            # Увеличиваем счётчики
            stats = self.stats_collection.find_one({"user_id": user_id}) or {}
            new_streak = stats.get("streak", 0) + 1
            new_max_streak = max(stats.get("max_streak", 0), new_streak)
            
            self.stats_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"correct_answers": 1},
                    "$set": {
                        "streak": new_streak,
                        "max_streak": new_max_streak
                    }
                }
            )
            
            # Добавляем решённое слово
            if paronym_id and word:
                self.solved_words_collection.update_one(
                    {"user_id": user_id, "paronym_id": paronym_id, "word": word},
                    {"$setOnInsert": {"solved_at": None}},
                    upsert=True
                )
        else:
            # Неправильный ответ - только сбрасываем серию
            self.stats_collection.update_one(
                {"user_id": user_id},
                {"$set": {"streak": 0}}
            )
        
        # Обновляем username
        if username:
            self.stats_collection.update_one(
                {"user_id": user_id},
                {"$set": {"username": username}}
            )
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        leaderboard = list(self.stats_collection.find(
            {"correct_answers": {"$gt": 0}}
        ).sort([("correct_answers", -1), ("max_streak", -1)]).limit(limit))
        
        result = []
        for idx, stats in enumerate(leaderboard, 1):
            correct = stats.get("correct_answers", 0)
            
            result.append({
                "rank": idx,
                "user_id": stats["user_id"],
                "username": stats.get("username") or f"User {stats['user_id']}",
                "correct_answers": correct,
                "total_answers": correct,  # Для совместимости
                "percentage": 100.0,  # 100%, так как только правильные
                "max_streak": stats.get("max_streak", 0)
            })
        return result
    
    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя."""
        self.stats_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "total_answers": 0,
                    "correct_answers": 0,
                    "incorrect_answers": 0,
                    "streak": 0,
                    "max_streak": 0
                }
            }
        )
    
    def get_user_solved_words_count(self, user_id: int) -> int:
        """Возвращает количество уникальных решённых слов пользователя."""
        return self.solved_words_collection.count_documents({"user_id": user_id})

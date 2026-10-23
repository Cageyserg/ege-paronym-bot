"""
Модуль для работы с MongoDB.
Заменяет SQLite для постоянного хранения данных на Render.
"""

import os
import random
import logging
from typing import Dict, List, Any, Optional
from pymongo import MongoClient, ASCENDING
from config import QUESTIONS_FILE, ANSWERS_FILE
import json

logger = logging.getLogger(__name__)


class MongoDB:
    """Класс для управления базой данных MongoDB."""
    
    def __init__(self, mongo_uri: str = None):
        if mongo_uri is None:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

        logger.info(f"Подключение к MongoDB: {mongo_uri[:20]}...")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["ege_paronym_bot"]

        # Коллекции
        self.questions_collection = self.db["questions"]
        self.answers_collection = self.db["answers"]
        self.stats_collection = self.db["user_stats"]
        self.solved_words_collection = self.db["user_solved_words"]

        # Создаём индексы
        self._create_indexes()

        # Загружаем вопросы и ответы из JSON
        self._load_data_from_json()
        logger.info("MongoDB инициализирован успешно")
    
    def _create_indexes(self):
        """Создаёт индексы для оптимизации запросов."""
        self.questions_collection.create_index("id", unique=True)
        self.answers_collection.create_index("question_id", unique=True)
        self.stats_collection.create_index("user_id", unique=True)
        self.solved_words_collection.create_index(
            [("user_id", 1), ("question_id", 1), ("word", 1)],
            unique=True
        )
    
    def _load_data_from_json(self):
        """Загружает вопросы и ответы из JSON файлов."""
        # Проверяем, есть ли уже данные
        if self.questions_collection.count_documents({}) > 0:
            return
        
        # Загружаем вопросы
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
            
            for q in questions_data.get("questions", []):
                self.questions_collection.update_one(
                    {"id": q["id"]},
                    {
                        "$set": {
                            "id": q["id"],
                            "sentence": q["sentence"],
                            "explanation": q["explanation"]
                        }
                    },
                    upsert=True
                )
        
        # Загружаем ответы
        if os.path.exists(ANSWERS_FILE):
            with open(ANSWERS_FILE, 'r', encoding='utf-8') as f:
                answers_data = json.load(f)
            
            for a in answers_data.get("answers", []):
                self.answers_collection.update_one(
                    {"question_id": a["question_id"]},
                    {
                        "$set": {
                            "question_id": a["question_id"],
                            "correct": a["correct"],
                            "wrong": a["wrong"]
                        }
                    },
                    upsert=True
                )
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос с перемешанными вариантами ответов."""
        # Получаем случайный вопрос
        pipeline = [{"$sample": {"size": 1}}]
        questions = list(self.questions_collection.aggregate(pipeline))
        
        if not questions:
            return None
        
        question = questions[0]
        
        # Получаем ответы для этого вопроса
        answer = self.answers_collection.find_one({"question_id": question["id"]})
        
        if not answer:
            return None
        
        # Формируем список вариантов: правильный + неправильные
        all_words = [answer["correct"]] + answer["wrong"]
        
        # Перемешиваем варианты
        random.shuffle(all_words)
        
        return {
            "question_id": question["id"],
            "sentence": question["sentence"],
            "explanation": question["explanation"],
            "correct": answer["correct"],
            "words": all_words
        }
    
    def get_user_stats(self, user_id: int, username: str = None) -> Dict[str, int]:
        """Возвращает статистику пользователя."""
        stats = self.stats_collection.find_one({"user_id": user_id})
        
        if not stats:
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
    
    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None, question_id: int = None, word: str = None):
        """Обновляет статистику пользователя."""
        logger.info(f"MongoDB update_user_stats: user_id={user_id}, is_correct={is_correct}, username={username}")
        if is_correct:
            stats = self.stats_collection.find_one({"user_id": user_id}) or {}
            new_streak = stats.get("streak", 0) + 1
            new_max_streak = max(stats.get("max_streak", 0), new_streak)

            result = self.stats_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"correct_answers": 1},
                    "$set": {
                        "streak": new_streak,
                        "max_streak": new_max_streak
                    }
                },
                upsert=True
            )
            logger.info(f"Update result: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")

            if question_id and word:
                self.solved_words_collection.update_one(
                    {"user_id": user_id, "question_id": question_id, "word": word},
                    {"$setOnInsert": {"solved_at": None}},
                    upsert=True
                )
        else:
            result = self.stats_collection.update_one(
                {"user_id": user_id},
                {"$set": {"streak": 0}},
                upsert=True
            )
            logger.info(f"Reset streak result: matched={result.matched_count}, modified={result.modified_count}")

        if username:
            result = self.stats_collection.update_one(
                {"user_id": user_id},
                {"$set": {"username": username}}
            )
            logger.info(f"Update username result: matched={result.matched_count}, modified={result.modified_count}")
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        logger.info(f"Запрос leaderboard с limit={limit}")
        leaderboard = list(self.stats_collection.find(
            {"correct_answers": {"$gt": 0}}
        ).sort([("correct_answers", -1)]).limit(limit))

        logger.info(f"Найдено {len(leaderboard)} записей в leaderboard")
        result = []
        for idx, stats in enumerate(leaderboard, 1):
            correct = stats.get("correct_answers", 0)
            result.append({
                "rank": idx,
                "user_id": stats["user_id"],
                "username": stats.get("username") or f"User {stats['user_id']}",
                "correct_answers": correct,
                "total_answers": correct,
                "percentage": 100.0,
                "max_streak": 0
            })
        return result
    
    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя."""
        self.stats_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "correct_answers": 0,
                    "streak": 0,
                    "max_streak": 0
                }
            }
        )
    
    def get_user_solved_words_count(self, user_id: int) -> int:
        """Возвращает количество уникальных решённых слов пользователя."""
        return self.solved_words_collection.count_documents({"user_id": user_id})

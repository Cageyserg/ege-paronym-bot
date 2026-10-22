"""
Модуль для работы с данными вопросов и ответов.
"""

import os
from typing import Dict, List, Any, Optional
from config import USE_MONGODB, MONGODB_URI

# Импортируем нужный класс базы данных
if USE_MONGODB:
    from utils.mongodb import MongoDB
    DatabaseClass = MongoDB
else:
    from utils.database import Database
    DatabaseClass = Database


class DataManager:
    """Класс для управления данными вопросов и статистикой пользователей."""
    
    def __init__(self):
        if USE_MONGODB:
            self.db = MongoDB(MONGODB_URI)
        else:
            self.db = Database()
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос из базы."""
        return self.db.get_random_question()
    
    def get_user_stats(self, user_id: int, username: str = None) -> Dict[str, int]:
        """Возвращает статистику пользователя."""
        return self.db.get_user_stats(user_id, username)
    
    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None, question_id: int = None, word: str = None):
        """Обновляет статистику пользователя."""
        self.db.update_user_stats(user_id, is_correct, username, question_id, word)
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает таблицу лидеров."""
        return self.db.get_leaderboard(limit)
    
    def reset_user_stats(self, user_id: int):
        """Сбрасывает статистику пользователя."""
        self.db.reset_user_stats(user_id)
    
    def get_user_solved_words_count(self, user_id: int) -> int:
        """Возвращает количество уникальных решённых слов пользователя."""
        return self.db.get_user_solved_words_count(user_id)

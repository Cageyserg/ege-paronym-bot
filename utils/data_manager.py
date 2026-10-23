"""
Модуль для работы с данными вопросов и ответов.
"""

import os
import json
import random
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
        
        # Загружаем задания из JSON файла
        self.tasks = self._load_tasks()
    
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Загружает задания из paronyms.json."""
        try:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(script_dir, 'data', 'paronyms.json')
            
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Новый формат: список заданий без обёртки 'tasks'
                if isinstance(data, list):
                    return data
                return data.get('tasks', [])
        except Exception as e:
            print(f"Ошибка загрузки заданий: {e}")
            return []
    
    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос из файла."""
        if not self.tasks:
            return None

        task = random.choice(self.tasks)
        # Перемешиваем варианты ответов случайным образом
        import copy
        shuffled_options = copy.copy(task['options'])
        random.shuffle(shuffled_options)

        return {
            'id': task['id'],
            'task': task['task'],
            'options': shuffled_options,
            'correct_answer': task['correct_answer'],
            'explanation': task.get('explanation', '')
        }
    
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

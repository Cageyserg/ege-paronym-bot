"""
Управление данными и статистикой пользователей.
Использует SQLite для персистентности + in-memory кэш (StatsCache).

Архитектура:
- StatsCache — кэш в RAM с RLock, flush-поток каждые 10 сек, батч-запись в SQLite.
- DataManager — обёртка над StatsCache + загрузка вопросов из паронимов.json.
"""

import json
import os
import random
import copy
import logging
import threading
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ===================== StatsCache =====================
class StatsCache:
    """In-memory cache для user_stats. Все мутации — под RLock. Flush в БД каждые 10 сек."""

    def __init__(self):
        self._db = None
        self._cache: Dict[int, dict] = {}
        self._dirty: set = set()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._flush_thread = None
        self._loaded = False
        self._warned_no_db = False

    # ===================== LIFE CYCLE =====================

    def attach_db(self, db):
        """Подключает БД к существующему кэшу. При смене БД — flush старой перед очисткой."""
        with self._lock:
            if self._db is not None and self._db is not db:
                logger.warning("StatsCache: смена БД, flush старой перед переключением")
                try:
                    self.flush_to_db()   # self._db ещё СТАРАЯ — пишем в неё
                except Exception as e:
                    logger.error(f"flush старой БД не удался: {e}", exc_info=True)
                self._cache.clear()
                self._dirty.clear()
                self._loaded = False
            self._db = db

    def load_all_from_db(self):
        """Загружает ВСЮ таблицу user_stats из SQLite в кэш при старте."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            logger.info("StatsCache: загрузка статистики пользователей из SQLite...")
            rows = self._db.get_all_user_stats()
            for row in rows:
                uid = row["user_id"]
                self._cache[uid] = {
                    "_uid": uid,
                    "username": row.get("username") or "Anonymous",
                    "firstname": row.get("firstname") or "",
                    "correct_answers": row.get("correct_answers", 0),
                    "streak": row.get("streak", 0),
                    "max_streak": row.get("max_streak", 0),
                }
            self._loaded = True
            logger.info(f"StatsCache: загружено {len(self._cache)} пользователей")

    def start_flush_loop(self):
        """Запускает фоновый поток для периодической записи dirty в БД."""
        if self._flush_thread is not None and self._flush_thread.is_alive():
            return
        self._stop_event.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop_worker, daemon=True)
        self._flush_thread.start()
        logger.info("StatsCache flush loop started")

    def _flush_loop_worker(self):
        """Фоновый поток: каждые 10 сек записывает dirty данные в БД."""
        while not self._stop_event.wait(10.0):
            try:
                self.flush_to_db()
            except Exception as e:
                logger.error(f"flush loop error: {e}", exc_info=True)

    def stop_flush_loop(self):
        """Останавливает поток, делает финальный flush. Идемпотентен."""
        self._stop_event.set()
        t = self._flush_thread
        if t is not None and t.is_alive() and threading.current_thread() is not t:
            t.join(timeout=5.0)
        self._flush_thread = None
        try:
            self.flush_to_db()
        except Exception as e:
            logger.error(f"final flush error: {e}", exc_info=True)
        logger.info("StatsCache stopped")

    # ===================== READ (memory only, DB miss-safe) =====================

    def _create_empty_user(self, user_id: int):
        """Создаёт запись пользователя в кэше с default значениями + помечает dirty."""
        self._cache[user_id] = {
            "_uid": user_id, "username": "Anonymous", "firstname": "",
            "correct_answers": 0, "streak": 0, "max_streak": 0,
        }

    def get_user_stats(self, user_id: int, username: str = None, firstname: str = None) -> dict:
        """Возвращает статистику из кэша. При первом обращении — создает default запись."""
        with self._lock:
            if user_id not in self._cache:
                self._create_empty_user(user_id)
                self._dirty.add(user_id)
            stats = self._cache[user_id]

        # Обновляем имя только при реальных изменениях — НЕ пишем в БД без изменений
        if username and stats["username"] != username:
            with self._lock:
                stats["username"] = username
                self._dirty.add(user_id)
        if firstname and stats["firstname"] != firstname:
            with self._lock:
                stats["firstname"] = firstname
                self._dirty.add(user_id)

        return dict(stats)

    def get_leaderboard_from_cache(self, limit: int = 20) -> List[dict]:
        """Возвращает таблицу лидеров из кэша."""
        with self._lock:
            sorted_users = sorted(
                (s for s in self._cache.values() if s["correct_answers"] > 0),
                key=lambda x: x["correct_answers"], reverse=True
            )[:limit]

            return [
                {
                    "rank": idx + 1,
                    "user_id": s["_uid"],
                    "username": s.get("username") or f"User {s['_uid']}",
                    "correct_answers": s["correct_answers"],
                    "total_answers": s["correct_answers"],
                    "percentage": 100.0,
                    "max_streak": s.get("max_streak", 0),
                }
                for idx, s in enumerate(sorted_users)
            ]

    # ===================== WRITE (memory only) =====================

    def update_user_stats(self, user_id: int, is_correct: bool, username: str = None,
                          firstname: str = None, question_id: int = None, word: str = None):
        """Обновляет статистику ТОЛЬКО В ПАМЯТИ. Помечает user_id dirty для батч-записи."""
        with self._lock:
            if user_id not in self._cache:
                self._create_empty_user(user_id)
                self._dirty.add(user_id)

            s = self._cache[user_id]

            # Смена имени/отчества — два независимых if (не elif!)
            if username and s["username"] != username:
                s["username"] = username
                self._dirty.add(user_id)
            if firstname and s["firstname"] != firstname:
                s["firstname"] = firstname
                self._dirty.add(user_id)

            # Обновляем ответы
            if is_correct:
                s["correct_answers"] += 1
                s["streak"] += 1
                if s["streak"] > s["max_streak"]:
                    s["max_streak"] = s["streak"]
                self._dirty.add(user_id)
            else:
                s["streak"] = 0
                self._dirty.add(user_id)

    def flush_to_db(self):
        """Батч-запись dirty записей в SQLite одним INSERT OR REPLACE."""
        # Предупреждение об отсутствии БД (один раз)
        if self._db is None:
            if not self._warned_no_db:
                self._warned_no_db = True
                logger.warning("StatsCache: БД не подключена — данные не сохраняются")
            return

        if not self._dirty:
            return

        # a) Snapshot + clear под единым локом
        with self._lock:
            dirty_ids = list(self._dirty)
            self._dirty.clear()

        try:
            # b) Читаем cache данные (отдельный блок лога)
            rows_to_insert = []
            with self._lock:
                for uid in dirty_ids:
                    if uid not in self._cache:
                        continue
                    s = self._cache[uid]
                    rows_to_insert.append((
                        uid, s["username"], s["firstname"],
                        s["correct_answers"], s["streak"], s["max_streak"],
                    ))

            # Запись в БД (вне лока — хендлеры не блокируются)
            if rows_to_insert:
                self._db.batch_update_user_stats(rows_to_insert)
                logger.debug(f"Flushed {len(rows_to_insert)} user(s)")

        except Exception as e:
            # c) При ошибке возвращаем все dirty IDs обратно
            logger.error(f"flush_to_db failed, re-queuing {len(dirty_ids)} user(s): {e}", exc_info=True)
            with self._lock:
                for uid in dirty_ids:
                    self._dirty.add(uid)

    def reset_user_stats_for_id(self, user_id: int):
        """Сбрасывает статистику пользователя в кэше."""
        with self._lock:
            if user_id in self._cache:
                s = self._cache[user_id]
                s["correct_answers"] = 0
                s["streak"] = 0
                s["max_streak"] = 0
                self._dirty.add(user_id)

    def get_all_stats(self):
        """Возвращает копию всего кэша (для отладки)."""
        with self._lock:
            return dict(self._cache)


# ===================== DataManager (wrapper + singleton) =====================

class DataManager:
    """Управление вопросами и статистикой. Использует StatsCache для user_stats."""

    def __init__(self):
        logger.info("DataManager: инициализация (загрузка паронимов.json)...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, '..', 'data', 'paronyms.json')
        self.tasks = self._load_tasks(data_path)
        self.stats_cache = StatsCache()
        logger.info(f"DataManager: загружено {len(self.tasks)} заданий")

    def _load_tasks(self, path):
        """Загружает задания из paronyms.json."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get('tasks', [])
        except Exception as e:
            logger.error(f"Ошибка загрузки паронимов: {e}")
            return []

    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайный вопрос с перемешанными вариантами."""
        if not self.tasks:
            return None
        task = random.choice(self.tasks)
        shuffled = copy.copy(task['options'])
        random.shuffle(shuffled)
        return {
            'id': task['id'],
            'task': task.get('task') or task.get('question'),
            'options': shuffled,
            'correct_answer': task['correct_answer'],
            'explanation': task.get('explanation', ''),
            'word': task.get('word', ''),
        }

    def get_user_stats(self, user_id, username=None, firstname=None):
        return self.stats_cache.get_user_stats(user_id, username, firstname)

    def update_user_stats(self, user_id, is_correct, username=None, firstname=None, question_id=None, word=None):
        self.stats_cache.update_user_stats(user_id, is_correct, username, firstname, question_id, word)

    def get_leaderboard(self, limit=10):
        return self.stats_cache.get_leaderboard_from_cache(limit)

    def reset_user_stats(self, user_id):
        self.stats_cache.reset_user_stats_for_id(user_id)

    def start_flush_loop(self):
        self.stats_cache.start_flush_loop()

    def stop_flush_loop(self):
        self.stats_cache.stop_flush_loop()


# ===================== MODULE SINGLETON + INIT =====================

data_manager = DataManager()  # Загружает paronyms.json ОДИН раз при импорте модуля


def init_data_manager(db=None):
    """
    ИДЕМПОТЕНТНАЯ инициализация (IN-PLACE, без перепривязки глобала):
    1. Подключаем БД к существующему экземпляру.
    2. Загружаем данные из БД в кэш (один раз).

    Возвращает ссылку на модульный экземпляр data_manager.
    """
    if db is None:
        logger.warning("init_data_manager(db=None) — DataManager без БД!")
        return data_manager

    old_db = data_manager.stats_cache._db
    if old_db is not None and old_db != db:
        logger.warning("init_data_manager: заменяем старую БД на новую")

    data_manager.stats_cache.attach_db(db)
    data_manager.stats_cache.load_all_from_db()

    logger.info("DataManager инициализирован: DB подключен, кэш загружен")
    return data_manager

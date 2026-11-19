"""
Хранилище состояния тренировки в памяти процесса.

Два ограниченных по размеру контейнера:
- QuizStore — активное задание и блокировка на пользователя;
- BoundedDict — LRU-словарь (id последних сообщений с таблицей лидеров на чат).

Оба не растут бесконечно: при переполнении вытесняются самые старые записи,
поэтому долгоживущий процесс не течёт памятью.
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Iterator
from typing import Any


class BoundedDict(OrderedDict):
    """OrderedDict с ограничением размера: старые ключи вытесняются первыми."""

    def __init__(self, maxsize: int = 1000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxsize = max(1, int(maxsize))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().move_to_end(key)
        while len(self) > self.maxsize:
            self.popitem(last=False)

    def get_lru(self, key, default=None):
        """Чтение с поднятием ключа в конец очереди."""
        if key not in self:
            return default
        super().move_to_end(key)
        return self[key]


class QuizStore:
    """Активные задания пользователей + по-юзерные блокировки, с вытеснением."""

    def __init__(self, max_users: int = 50000):
        self._max_users = max(10, int(max_users))
        self._state: dict[int, dict] = {}
        self._locks: dict[int, threading.Lock] = {}
        self._seen: dict[int, float] = {}
        self._guard = threading.Lock()

    # ---------- блокировки ----------

    def lock_for(self, user_id: int) -> threading.Lock:
        """Блокировка пользователя (сериализует обработку его колбэков)."""
        with self._guard:
            self._seen[user_id] = time.monotonic()
            lock = self._locks.get(user_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[user_id] = lock
            self._evict()
            return lock

    # ---------- состояние ----------

    def get(self, user_id: int) -> dict | None:
        with self._guard:
            return self._state.get(user_id)

    def set(self, user_id: int, state: dict):
        with self._guard:
            self._state[user_id] = state
            self._seen[user_id] = time.monotonic()
            self._evict()

    def pop(self, user_id: int) -> dict | None:
        with self._guard:
            self._seen[user_id] = time.monotonic()
            return self._state.pop(user_id, None)

    def size(self) -> int:
        with self._guard:
            return len(self._state)

    def __contains__(self, user_id: int) -> bool:
        return self.get(user_id) is not None

    def clear(self):
        with self._guard:
            self._state.clear()

    # ---------- вытеснение ----------

    def _evict(self):
        """Удаляет старейших пользователей без активного задания."""
        overflow = len(self._locks) - self._max_users
        if overflow <= 0:
            return
        idle = [
            uid for uid in self._locks
            if self._state.get(uid) is None or self._state[uid].get("done")
        ]
        idle.sort(key=lambda uid: self._seen.get(uid, 0.0))
        for uid in idle[:overflow]:
            self._locks.pop(uid, None)
            self._state.pop(uid, None)
            self._seen.pop(uid, None)

    def __iter__(self) -> Iterator[int]:
        return iter(list(self._state))


def new_state(question: dict[str, Any]) -> dict:
    """Состояние одного задания из вопроса DataManager."""
    return {
        "qid": question["id"],
        "attempt": 0,
        "options": list(question["options"]),
        "correct": question["correct_answer"],
        "explanation": question.get("explanation", ""),
        "task": question["task"],
        "done": False,
    }

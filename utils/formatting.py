"""
Форматирование текста для Telegram (Markdown) и подписи пользователей.

Единая точка правды: имена/ники экранируются здесь, чтобы parse_mode='Markdown'
не падал на символах вроде «*», «_», «[», «`» в нике или имени.
"""

from collections.abc import Mapping
from typing import Any

# Символы, ломающие parse_mode='Markdown' в Telegram.
# Обратная косая черта обязана быть первой, иначе экранируются и её же вставки.
_MD_SPECIALS = ("\\", "_", "*", "[", "]", "`")


def md_escape(value: Any | None) -> str:
    """Экранирует спецсимволы Markdown. None превращается в пустую строку."""
    text = "" if value is None else str(value)
    for ch in _MD_SPECIALS:
        text = text.replace(ch, "\\" + ch)
    return text


def _clean(value: Any | None) -> str:
    return "" if value is None else str(value).strip()


def display_name(stats: Mapping[str, Any]) -> str:
    """Подпись для таблицы лидеров: имя профиля → @username → «Без имени»."""
    first = _clean(stats.get("firstname"))
    if first and first != "Anonymous":
        return first
    uname = _clean(stats.get("username")).lstrip("@")
    if uname and uname != "Anonymous":
        return "@" + uname
    return "Без имени"


def user_label(username: str | None, firstname: str | None) -> str:
    """
    Подпись для экрана статистики: «@ник (Имя)» / «@ник» / «Имя» / «без имени».

    Никогда не показывает «@Anonymous» или «@None»: если username отсутствует,
    остаётся только имя, а если нет и его — нейтральное «без имени».
    """
    uname = _clean(username).lstrip("@")
    first = _clean(firstname)
    if uname in ("Anonymous", "None"):
        uname = ""
    if first in ("Anonymous", "None"):
        first = ""

    if uname and first:
        return f"@{uname} ({first})"
    if uname:
        return f"@{uname}"
    if first:
        return first
    return "без имени"

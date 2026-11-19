"""
Форматирование текста для Telegram (Markdown) и подписи пользователей.

Единая точка правды: имена/ники экранируются здесь, чтобы parse_mode='Markdown'
не падал на символах вроде «*», «_», «[», «`» в нике или имени.
"""

import unicodedata
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


def _is_zero_width(ch: str) -> bool:
    """Символы, не занимающие клетку сами по себе (склейки, селекторы, модификаторы)."""
    cp = ord(ch)
    return (
        unicodedata.combining(ch) != 0
        or unicodedata.category(ch) in ("Mn", "Me", "Cf")
        or 0xFE00 <= cp <= 0xFE0F  # variation selectors
        or 0x1F3FB <= cp <= 0x1F3FF  # тон кожи
        or 0xE0020 <= cp <= 0xE007F  # теги (флаги субрегионов)
    )


# Диапазоны, где Unicode-таблица помечает символы узкими (east_asian_width = N),
# а Telegram рисует их широкими эмодзи. Проверено на реальных никах из лидерборда:
# 🌧 (U+1F327) в таблице «нейтральный», но рендерится как двухклеточный.
#
# Только SMP: символы BMP вроде ✿ (U+273F) и ◕ (U+25D5) Telegram рисует
# текстовым начертанием, и они действительно занимают одну клетку.
_WIDE_EMOJI_RANGES = (
    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F680, 0x1F6FF),  # Transport and Map Symbols
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
)


def _is_wide_emoji(ch: str) -> bool:
    """
    Широкий ли символ в рендере Telegram.

    `unicodedata.east_asian_width` знает не всё: 1159 эмодзи в SMP помечены там
    как «нейтральные», хотя рисуются во всю ширину. Поэтому дополнительно
    проверяем диапазоны, а не только таблицу.
    """
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return True
    cp = ord(ch)
    return any(start <= cp <= end for start, end in _WIDE_EMOJI_RANGES)


def _is_regional_indicator(ch: str) -> bool:
    """Пара таких символов рисуется одним флагом шириной в две клетки."""
    return 0x1F1E6 <= ord(ch) <= 0x1F1FF


def clusters(text: str) -> list[str]:
    """
    Разбивает строку на видимые кластеры — то, что человек считает «буквой».

    `👨‍👩‍👧‍👦` — один кластер, хотя это 7 кодовых точек; `🇷🇺` — один, хотя это
    две. Без такого разбиения выравнивание уезжает ровно на длину склейки.
    """
    out: list[str] = []
    current: list[str] = []
    pending_flag = False
    join_next = False

    for ch in text:
        if ch == "\u200d":  # ZWJ: следующий символ — продолжение картинки
            current.append(ch)
            join_next = True
            continue
        if _is_zero_width(ch):
            current.append(ch)
            continue
        if _is_regional_indicator(ch):
            if pending_flag:
                current.append(ch)
                out.append("".join(current))
                current = []
                pending_flag = False
            else:
                out.append("".join(current))
                current = [ch]
                pending_flag = True
            join_next = False
            continue
        if pending_flag:
            pending_flag = False
        if join_next:
            current.append(ch)
            join_next = False
            continue
        out.append("".join(current))
        current = [ch]

    out.append("".join(current))
    return [c for c in out if c]


def display_width(text: str) -> int:
    """
    Ширина строки в «клетках» моноширинного шрифта Telegram.

    Считать `len()` нельзя: кириллица уже латиницы, эмодзи и CJK занимают две
    клетки, а составные последовательности (`👨‍👩‍👧‍👦`, `👍🏽`, `🇷🇺`, `⚔️`)
    рисуются одной картинкой, хотя состоят из нескольких кодовых точек.
    """
    width = 0
    for cluster in clusters(text):
        base = cluster[0]
        if _is_wide_emoji(base) or any(_is_wide_emoji(ch) for ch in cluster):
            width += 2
        elif "\ufe0f" in cluster:
            width += 2  # VS16 включает эмблемное начертание — оно широкое
        elif _is_regional_indicator(base):
            width += 2  # флаг целиком
        else:
            width += 1
    return width


def truncate_width(text: str, limit: int, ellipsis: str = "…") -> str:
    """
    Обрезает строку до limit клеток, добавляя многоточие.

    Режется по кластерам: половина эмодзи в выводе выглядела бы мусором.
    """
    if display_width(text) <= limit:
        return text
    budget = limit - display_width(ellipsis)
    out: list[str] = []
    used = 0
    for cluster in clusters(text):
        w = display_width(cluster)
        if used + w > budget:
            break
        out.append(cluster)
        used += w
    return "".join(out) + ellipsis


def pad_width(text: str, limit: int) -> str:
    """Дополняет строку пробелами справа до limit клеток."""
    return text + " " * max(0, limit - display_width(text))


def code_safe(text: Any | None) -> str:
    """
    Обезвреживает текст для вставки в ```-блок.

    Обратная кавычка закрыла бы блок раньше времени, а перевод строки
    развалил бы колонки, поэтому и то и другое заменяется.
    """
    value = "" if text is None else str(text)
    return value.replace("`", "'").replace("\n", " ").replace("\r", " ").strip()

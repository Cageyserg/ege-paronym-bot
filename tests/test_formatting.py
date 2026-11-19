"""Тесты форматирования: экранирование Markdown и подписи пользователей."""

from utils.formatting import display_name, md_escape, user_label


def test_md_escape_specials():
    assert md_escape("a_b*c[d]`e\\f") == "a\\_b\\*c\\[d\\]\\`e\\\\f"
    assert md_escape("x[y]") == "x\\[y\\]"


def test_md_escape_none_and_numbers():
    assert md_escape(None) == ""
    assert md_escape(15) == "15"


def test_md_escape_keeps_plain_text():
    assert md_escape("обычный текст") == "обычный текст"


def test_display_name_prefers_firstname():
    assert display_name({"firstname": "Иван", "username": "ivan"}) == "Иван"


def test_display_name_falls_back_to_username():
    assert display_name({"firstname": "", "username": "ivan"}) == "@ivan"


def test_display_name_never_shows_anonymous():
    assert display_name({"firstname": "Anonymous", "username": "Anonymous"}) == "Без имени"
    assert display_name({}) == "Без имени"


def test_user_label_both_parts():
    assert user_label("ivan", "Иван") == "@ivan (Иван)"


def test_user_label_username_only():
    assert user_label("ivan", None) == "@ivan"


def test_user_label_no_username():
    """Раньше здесь появлялось «@None» / «@Anonymous»."""
    assert user_label(None, "Иван") == "Иван"
    assert user_label("Anonymous", "Иван") == "Иван"
    assert user_label(None, None) == "без имени"
    assert user_label("", "") == "без имени"


def test_user_label_strips_at_sign():
    assert user_label("@ivan", "Иван") == "@ivan (Иван)"




def test_truncate_keeps_short_text():
    from utils.formatting import truncate

    assert truncate("Яна", 24) == "Яна"


def test_truncate_shortens_long_text():
    from utils.formatting import truncate

    result = truncate("Очень-очень длинное имя пользователя", 24)
    assert len(result) <= 24
    assert result.endswith("…")


def test_truncate_collapses_whitespace():
    """Перевод строки в нике развалил бы строку таблицы."""
    from utils.formatting import truncate

    assert truncate("Вася\nПупкин", 24) == "Вася Пупкин"
    assert truncate("  много   пробелов  ", 24) == "много пробелов"


def test_truncate_handles_none():
    from utils.formatting import truncate

    assert truncate(None, 24) == ""

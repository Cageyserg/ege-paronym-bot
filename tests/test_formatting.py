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


def test_display_width_counts_cyrillic_as_one_cell():
    from utils.formatting import display_width

    assert display_width("Яна") == 3
    assert display_width("Cageyserg") == 9


def test_display_width_counts_emoji_as_two_cells():
    from utils.formatting import display_width

    assert display_width("🍂") == 2
    assert display_width("Аскер🍂🌧🦊") == 10


def test_display_width_treats_zwj_sequence_as_single_emoji():
    """👨‍👩‍👧‍👦 — 7 кодовых точек, но одна картинка шириной 2."""
    from utils.formatting import display_width

    assert display_width("👨‍👩‍👧‍👦") == 2


def test_display_width_treats_flag_as_single_emoji():
    from utils.formatting import display_width

    assert display_width("🇷🇺") == 2


def test_display_width_handles_variation_selector():
    """⚔️ с VS16 — эмблемное начертание, шириной 2; ⚔ без него — 1."""
    from utils.formatting import display_width

    assert display_width("⚔️") == 2
    assert display_width("⚔") == 1


def test_display_width_ignores_skin_tone_modifier():
    from utils.formatting import display_width

    assert display_width("👍🏽") == 2


def test_display_width_ignores_zero_width_space():
    from utils.formatting import display_width

    # Невидимый ZWSP не занимает клетку: видимых символов четыре.
    assert display_width("Ва\u200bся") == 4


def test_truncate_width_does_not_split_emoji():
    from utils.formatting import display_width, truncate_width

    family = "👨‍👩‍👧‍👦"
    result = truncate_width(family * 3, 5)
    # Бюджет 4 клетки = две целые семьи по 2 клетки плюс многоточие.
    assert result == family * 2 + "…"
    assert display_width(result) == 5


def test_pad_width_uses_cells_not_len():
    from utils.formatting import display_width, pad_width

    assert display_width(pad_width("🍂", 6)) == 6
    assert display_width(pad_width("абв", 6)) == 6
    assert display_width(pad_width("абвгд", 3)) == 5  # короче не режем

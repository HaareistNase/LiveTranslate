from hallucination_filter import (
    is_known_hallucination,
    is_translation_explosion,
    strip_known_hallucinations,
)


def test_removes_continued_phrase_but_keeps_real_text():
    text = (
        "Живем Продолжение следует... "
        "Продолжение следует.... "
        "Чего и вам желаем."
    )

    cleaned = strip_known_hallucinations(
        text
    )

    assert "Продолжение" not in cleaned
    assert "Живем" in cleaned
    assert "Чего и вам желаем" in cleaned


def test_only_hallucination_is_rejected():
    assert is_known_hallucination(
        "Продолжение следует..."
    )


def test_normal_translation_is_not_rejected():
    assert not is_translation_explosion(
        "Сейчас мои дети спят",
        "Meine Kinder schlafen jetzt."
    )


def test_repeated_translation_explosion_is_rejected():
    source = "Продолжение следует"

    target = (
        "Es geht weiter weiter weiter weiter weiter "
        "weiter weiter weiter weiter weiter weiter "
        "weiter weiter weiter weiter weiter weiter "
        "weiter weiter weiter weiter"
    )

    assert is_translation_explosion(
        source,
        target
    )

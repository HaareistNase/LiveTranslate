import context_buffer as module
from context_buffer import ContextBuffer


def test_short_sentences_are_grouped(monkeypatch):
    monkeypatch.setattr(
        module,
        "CONTEXT_TARGET_CHARACTERS",
        45
    )

    buffer = ContextBuffer()

    assert buffer.add_confirmed(
        "Erster kurzer Satz."
    ) == []

    blocks = buffer.add_confirmed(
        "Zweiter kurzer Satz. "
        "Dritter kurzer Satz."
    )

    assert blocks == [
        (
            "Erster kurzer Satz. "
            "Zweiter kurzer Satz. "
            "Dritter kurzer Satz."
        )
    ]


def test_partial_sentence_stays_during_pause():
    buffer = ContextBuffer()

    buffer.add_confirmed(
        "Ein vollständiger Satz. "
        "Dieser Satz ist noch nicht fertig"
    )

    buffer.last_update = 0

    blocks = buffer.flush_if_old()

    assert blocks == [
        "Ein vollständiger Satz."
    ]

    assert (
        buffer.partial
        == "Dieser Satz ist noch nicht fertig"
    )


def test_only_partial_is_released_after_timeout():
    buffer = ContextBuffer()

    buffer.add_confirmed(
        "Ein langer Satz ohne abschließendes Satzzeichen"
    )

    buffer.last_update = 0

    blocks = buffer.flush_if_old()

    assert blocks == [
        "Ein langer Satz ohne abschließendes Satzzeichen"
    ]


def test_hallucination_phrase_is_still_removed():
    buffer = ContextBuffer()

    blocks = buffer.add_confirmed(
        "Echter Text. Продолжение следует..."
    )

    assert all(
        "Продолжение" not in block
        for block in blocks
    )

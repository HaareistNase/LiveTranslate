from subtitle_postprocessor import (
    SubtitlePostprocessor,
)


def test_spacing_is_cleaned():
    processor = SubtitlePostprocessor()

    assert processor.process(
        "Hallo ,mein Name ist Andrei ."
    ) == [
        "Hallo, mein Name ist Andrei."
    ]


def test_adjacent_duplicate_sentence_is_removed():
    processor = SubtitlePostprocessor()

    assert processor.process(
        "Wir fahren los. Wir fahren los. "
        "Danach gehen wir nach Hause."
    ) == [
        (
            "Wir fahren los. "
            "Danach gehen wir nach Hause."
        )
    ]


def test_single_word_fragment_is_held_and_joined():
    processor = SubtitlePostprocessor()

    assert processor.process(
        "Wälder"
    ) == []

    assert processor.process(
        "und verschneite Wege sehen wunderschön aus."
    ) == [
        (
            "Wälder und verschneite Wege "
            "sehen wunderschön aus."
        )
    ]


def test_complete_short_sentence_is_not_held():
    processor = SubtitlePostprocessor()

    assert processor.process(
        "Danke."
    ) == [
        "Danke."
    ]


def test_pending_fragment_is_flushed_at_stop():
    processor = SubtitlePostprocessor()

    assert processor.process(
        "Wälder"
    ) == []

    assert processor.flush() == [
        "Wälder"
    ]

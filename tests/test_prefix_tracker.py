from transcript_assembler import (
    TranscriptAssembler,
)


def item(
    text: str,
    start: str = "0:00:00.08",
    end: str = "0:00:01.00"
) -> dict:
    return {
        "speaker": 1,
        "start": start,
        "end": end,
        "text": text,
    }


def test_intermediate_commit_keeps_prefix():
    tracker = TranscriptAssembler()

    tracker.add_item(
        item(
            "Здравствуйте меня зовут Андрей"
        )
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == "Здравствуйте меня зовут Андрей"
    )

    tracker.add_item(
        item(
            "Здравствуйте меня зовут Андрей "
            "я русский живу в Сибири",
            end="0:00:08.00"
        )
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == "я русский живу в Сибири"
    )


def test_repeated_same_text_outputs_nothing():
    tracker = TranscriptAssembler()

    tracker.add_item(
        item("Один и тот же текст")
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == "Один и тот же текст"
    )

    tracker.add_item(
        item(
            "Один и тот же текст",
            end="0:00:02.00"
        )
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == ""
    )


def test_new_start_finishes_old_line():
    tracker = TranscriptAssembler()

    tracker.add_item(
        item("Первая строка")
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == "Первая строка"
    )

    result = tracker.add_item(
        item(
            "Вторая строка",
            start="0:00:20.00",
            end="0:00:21.00"
        )
    )

    assert result == ""

    assert (
        tracker.flush_all()
        == "Вторая строка"
    )


def test_long_same_key_never_repeats_prefix():
    tracker = TranscriptAssembler()

    first = (
        "сейчас мои дети спят "
        "я пока записываю это видео"
    )

    second = (
        first
        + " скоро они проснутся "
        + "я их покормлю"
    )

    third = (
        second
        + " и мы пойдем на горку"
    )

    tracker.add_item(
        item(first)
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == first
    )

    tracker.add_item(
        item(
            second,
            end="0:00:20.00"
        )
    )

    assert (
        tracker.flush_stale(
            maximum_age_seconds=0
        )
        == "скоро они проснутся я их покормлю"
    )

    tracker.add_item(
        item(
            third,
            end="0:00:30.00"
        )
    )

    assert (
        tracker.flush_all()
        == "и мы пойдем на горку"
    )

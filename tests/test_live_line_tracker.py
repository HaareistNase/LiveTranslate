from transcript_assembler import (
    TranscriptAssembler,
)


def item(
    text: str,
    start: str = "0:00:00.00",
    end: str = "0:00:01.00"
) -> dict:
    return {
        "speaker": 1,
        "start": start,
        "end": end,
        "text": text,
    }


def test_growing_line_emits_nothing_until_finalized():
    tracker = TranscriptAssembler()

    assert tracker.add_item(
        item("Меня зовут Анд")
    ) == ""

    assert tracker.add_item(
        item(
            "Меня зовут Андрей, я",
            end="0:00:02.00"
        )
    ) == ""

    assert tracker.add_item(
        item(
            "Меня зовут Андрей, я русский",
            end="0:00:03.00"
        )
    ) == ""

    assert (
        tracker.flush_all()
        == "Меня зовут Андрей, я русский"
    )


def test_new_start_finalizes_previous_full_line():
    tracker = TranscriptAssembler()

    assert tracker.add_item(
        item("Первое предложение")
    ) == ""

    result = tracker.add_item(
        item(
            "Второе предложение",
            start="0:00:03.00",
            end="0:00:04.00"
        )
    )

    assert result == "Первое предложение"

    assert (
        tracker.flush_all()
        == "Второе предложение"
    )

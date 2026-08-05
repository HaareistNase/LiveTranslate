from transcript_assembler import TranscriptAssembler


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


def test_does_not_split_russian_words():
    assembler = TranscriptAssembler()

    assert assembler.add_item(
        item("Меня зовут Анд")
    ) == "Меня зовут"

    assert assembler.add_item(
        item(
            "Меня зовут Андрей, я",
            end="0:00:02.00"
        )
    ) == "Андрей,"

    assert assembler.add_item(
        item(
            "Меня зовут Андрей, я русский",
            end="0:00:03.00"
        )
    ) == "я"

    assert assembler.flush_all() == "русский"


def test_new_line_flushes_previous_last_word():
    assembler = TranscriptAssembler()

    assert assembler.add_item(
        item("Первый текст")
    ) == "Первый"

    result = assembler.add_item(
        item(
            "Второй текст",
            start="0:00:02.00",
            end="0:00:03.00"
        )
    )

    assert result == "текст Второй"
    assert assembler.flush_all() == "текст"

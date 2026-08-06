from transcript_assembler import (
    TranscriptAssembler,
    find_word_overlap,
    get_growth_suffix,
)


def test_same_timestamp_can_grow():
    assembler = TranscriptAssembler()

    assert assembler.add_item(
        {
            "start": 1.0,
            "end": 2.0,
            "text": "Das ist"
        }
    ) == "Das ist"

    assert assembler.add_item(
        {
            "start": 1.0,
            "end": 2.0,
            "text": "Das ist ein Test."
        }
    ) == "ein Test."


def test_identical_same_timestamp_is_ignored():
    assembler = TranscriptAssembler()

    item = {
        "start": 1.0,
        "end": 2.0,
        "text": "Hallo Welt."
    }

    assert assembler.add_item(item) == "Hallo Welt."
    assert assembler.add_item(item) == ""


def test_new_timestamp_is_new_line():
    assembler = TranscriptAssembler()

    assert assembler.add_item(
        {
            "start": 1.0,
            "end": 2.0,
            "text": "Erster Satz."
        }
    ) == "Erster Satz."

    assert assembler.add_item(
        {
            "start": 2.0,
            "end": 3.0,
            "text": "Zweiter Satz."
        }
    ) == "Zweiter Satz."


def test_overlap():
    assert find_word_overlap(
        "Heute gehen wir nach Hause",
        "nach Hause und schlafen"
    ) == 2


def test_growth_suffix():
    assert get_growth_suffix(
        "Heute gehen wir",
        "Heute gehen wir nach Hause."
    ) == "nach Hause."


def test_same_start_different_end_is_same_growing_line():
    assembler = TranscriptAssembler()

    assert assembler.add_item(
        {
            "speaker": 1,
            "start": "0:00:00.00",
            "end": "0:00:02.00",
            "text": "Казалось, ребенку бежать"
        }
    ) == "Казалось, ребенку бежать"

    assert assembler.add_item(
        {
            "speaker": 1,
            "start": "0:00:00.00",
            "end": "0:00:02.32",
            "text": "Казалось, ребенку бежать и даже"
        }
    ) == "и даже"

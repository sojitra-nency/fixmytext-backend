"""
Tests for text_service — pure unit tests, no HTTP needed.
"""

import app.services.text_service as ts


def test_to_uppercase():
    assert ts.to_uppercase("hello world") == "HELLO WORLD"


def test_to_lowercase():
    assert ts.to_lowercase("HELLO WORLD") == "hello world"


def test_to_inverse_case():
    assert ts.to_inverse_case("Hello") == "hELLO"


def test_remove_extra_spaces():
    assert ts.remove_extra_spaces("  hello   world  ") == "hello world"


def test_remove_all_spaces():
    assert ts.remove_all_spaces("hello world") == "helloworld"


def test_reverse_text():
    assert ts.reverse_text("hello") == "olleh"


def test_sort_lines_asc():
    assert ts.sort_lines_asc("banana\napple\ncherry") == "apple\nbanana\ncherry"


def test_base64_encode():
    assert ts.base64_encode("hello") == "aGVsbG8="


def test_base64_decode():
    assert ts.base64_decode("aGVsbG8=") == "hello"

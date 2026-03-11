"""
Tests for TextService — pure unit tests, no HTTP needed.
"""

import pytest
from app.services.text_service import TextService


def test_to_uppercase():
    assert TextService.to_uppercase("hello world") == "HELLO WORLD"


def test_to_lowercase():
    assert TextService.to_lowercase("HELLO WORLD") == "hello world"


def test_to_inverse_case():
    assert TextService.to_inverse_case("Hello") == "hELLO"


def test_remove_extra_spaces():
    assert TextService.remove_extra_spaces("  hello   world  ") == "hello world"


def test_remove_all_spaces():
    assert TextService.remove_all_spaces("hello world") == "helloworld"


def test_reverse_text():
    assert TextService.reverse_text("hello") == "olleh"


def test_sort_lines_asc():
    assert TextService.sort_lines_asc("banana\napple\ncherry") == "apple\nbanana\ncherry"


def test_base64_encode():
    assert TextService.base64_encode("hello") == "aGVsbG8="


def test_base64_decode():
    assert TextService.base64_decode("aGVsbG8=") == "hello"

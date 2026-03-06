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


def test_analyze_word_count():
    result = TextService.analyze("Hello world. How are you?")
    assert result["word_count"] == 5


def test_analyze_character_count():
    result = TextService.analyze("Hi")
    assert result["character_count"] == 2

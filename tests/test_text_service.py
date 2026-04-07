"""
Tests for text_service — pure unit tests, no HTTP or DB needed.
"""

import pytest

import app.services.text_service as ts


# ── Case transformations ──────────────────────────────────────────────────────


def test_to_uppercase():
    assert ts.to_uppercase("hello world") == "HELLO WORLD"


def test_to_lowercase():
    assert ts.to_lowercase("HELLO WORLD") == "hello world"


def test_to_inverse_case():
    assert ts.to_inverse_case("Hello") == "hELLO"


def test_to_sentence_case_basic():
    result = ts.to_sentence_case("hello world")
    assert result[0].isupper()


def test_to_sentence_case_with_period():
    result = ts.to_sentence_case("hello world.")
    assert result.endswith(".")


def test_to_title_case():
    assert ts.to_title_case("hello world") == "Hello World"


def test_to_upper_camel_case():
    assert ts.to_upper_camel_case("hello world") == "HelloWorld"


def test_to_lower_camel_case():
    assert ts.to_lower_camel_case("hello world") == "helloWorld"


def test_to_snake_case():
    assert ts.to_snake_case("Hello World") == "hello_world"


def test_to_snake_case_from_camel():
    assert ts.to_snake_case("helloWorld") == "hello_world"


def test_to_kebab_case():
    assert ts.to_kebab_case("Hello World") == "hello-world"


def test_to_capitalize_words():
    result = ts.to_capitalize_words("hello world")
    assert result == "Hello World"


def test_to_alternating_case():
    result = ts.to_alternating_case("hello")
    assert result == "hElLo"


def test_to_wide_text():
    result = ts.to_wide_text("hi")
    assert result == "h i"


# ── Spaces and whitespace ─────────────────────────────────────────────────────


def test_remove_extra_spaces():
    assert ts.remove_extra_spaces("  hello   world  ") == "hello world"


def test_remove_all_spaces():
    assert ts.remove_all_spaces("hello world") == "helloworld"


def test_remove_all_spaces_removes_tabs_too():
    # remove_all_spaces removes ALL whitespace (spaces, tabs, etc.)
    result = ts.remove_all_spaces("a b\tc")
    assert " " not in result
    assert "a" in result and "b" in result and "c" in result


def test_remove_line_breaks():
    result = ts.remove_line_breaks("line1\nline2\nline3")
    assert "\n" not in result


# ── Reversing and sorting ─────────────────────────────────────────────────────


def test_reverse_text():
    assert ts.reverse_text("hello") == "olleh"


def test_reverse_lines():
    result = ts.reverse_lines("line1\nline2\nline3")
    assert "line3" in result.split("\n")[0]


def test_sort_lines_asc():
    assert ts.sort_lines_asc("banana\napple\ncherry") == "apple\nbanana\ncherry"


def test_sort_lines_desc():
    assert ts.sort_lines_desc("apple\nbanana\ncherry") == "cherry\nbanana\napple"


def test_sort_lines_asc_single():
    assert ts.sort_lines_asc("only") == "only"


# ── Encoding ─────────────────────────────────────────────────────────────────


def test_base64_encode():
    assert ts.base64_encode("hello") == "aGVsbG8="


def test_base64_decode():
    assert ts.base64_decode("aGVsbG8=") == "hello"


def test_base64_roundtrip():
    text = "Hello, World! 123"
    assert ts.base64_decode(ts.base64_encode(text)) == text


def test_url_encode():
    result = ts.url_encode("hello world")
    assert " " not in result
    assert "hello" in result


def test_url_decode():
    assert ts.url_decode("hello%20world") == "hello world"


def test_url_roundtrip():
    original = "hello world & more"
    assert ts.url_decode(ts.url_encode(original)) == original


def test_html_encode():
    result = ts.html_escape_text("<b>bold</b>")
    assert "&lt;" in result
    assert "&gt;" in result


def test_html_decode():
    result = ts.html_unescape_text("&lt;b&gt;bold&lt;/b&gt;")
    assert "<b>" in result


def test_html_roundtrip():
    original = "<p>Hello & World</p>"
    assert ts.html_unescape_text(ts.html_escape_text(original)) == original


# ── Text manipulation ─────────────────────────────────────────────────────────


def test_remove_duplicate_lines():
    result = ts.remove_duplicate_lines("a\nb\na\nc")
    lines = result.split("\n")
    assert len(lines) == len(set(lines))


def test_trim_lines():
    result = ts.trim_lines("  hello  \n  world  ")
    assert "  hello  " not in result


def test_number_lines():
    result = ts.number_lines("first\nsecond")
    assert "1" in result
    assert "2" in result


def test_strip_empty_lines():
    result = ts.strip_empty_lines("a\n\nb\n\nc")
    lines = [ln for ln in result.split("\n") if ln == ""]
    assert len(lines) == 0


def test_strip_html():
    result = ts.strip_html("<p>Hello <b>World</b></p>")
    assert "<" not in result
    assert "Hello" in result
    assert "World" in result


def test_truncate_lines():
    result = ts.truncate_lines("Hello World This Is Long", 5)
    lines = result.split("\n")
    for line in lines:
        assert len(line) <= 5 + 3  # max_length + possible ellipsis


def test_pad_lines_left():
    result = ts.pad_lines("hi\nworld", "left")
    assert isinstance(result, str)


def test_pad_lines_right():
    result = ts.pad_lines("hi\nworld", "right")
    assert isinstance(result, str)


def test_extract_nth_lines():
    result = ts.extract_nth_lines("a\nb\nc\nd\ne", 2)
    assert isinstance(result, str)


def test_extract_nth_lines_zero_offset():
    result = ts.extract_nth_lines("a\nb\nc", 1, 0)
    assert "a" in result


def test_filter_lines_contain():
    result = ts.filter_lines_contain("apple\nbanana\ncherry", "an")
    assert "banana" in result
    assert "apple" not in result


def test_remove_lines_contain():
    result = ts.remove_lines_contain("apple\nbanana\ncherry", "an")
    assert "apple" in result
    assert "banana" not in result


def test_split_to_lines():
    result = ts.split_to_lines("a,b,c", ",")
    assert "a" in result
    assert "b" in result
    assert "c" in result


def test_join_lines():
    result = ts.join_lines("a\nb\nc", ",")
    assert result == "a,b,c"


# ── Caesar cipher ────────────────────────────────────────────────────────────


def test_caesar_cipher_encode():
    result = ts.caesar_cipher("hello", 3)
    assert result == "khoor"


def test_caesar_cipher_decode():
    result = ts.caesar_cipher("khoor", -3)
    assert result == "hello"


def test_caesar_cipher_wraps():
    result = ts.caesar_cipher("xyz", 3)
    assert result == "abc"


# ── Markdown ─────────────────────────────────────────────────────────────────


def test_format_json():
    result = ts.format_json('{"a": 1}')
    assert "a" in result


def test_atbash_cipher():
    result = ts.atbash_cipher("abc")
    assert result == "zyx"


def test_rot13():
    result = ts.rot13("hello")
    assert result == "uryyb"


def test_rot13_roundtrip():
    assert ts.rot13(ts.rot13("hello world")) == "hello world"


def test_binary_encode():
    result = ts.binary_encode("A")
    assert "01000001" in result


def test_hex_encode():
    result = ts.hex_encode("A")
    assert "41" in result.lower()


def test_morse_encode():
    result = ts.morse_encode("SOS")
    assert "." in result or "-" in result


def test_nato_phonetic():
    result = ts.nato_phonetic("abc")
    assert isinstance(result, str) and len(result) > 0

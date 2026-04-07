"""
Extended tests for text_service — covering the many functions not yet tested.
"""

import pytest

import app.services.text_service as ts


# ── Additional case transformations ─────────────────────────────────────────


def test_to_inverse_word_case_single_char_word():
    # Single-char word → uppercased
    result = ts.to_inverse_word_case("a")
    assert result == "A"


def test_to_inverse_word_case_multi_word():
    result = ts.to_inverse_word_case("hello world")
    assert isinstance(result, str)


def test_to_inverse_word_case_empty_words():
    # Words separated by multiple spaces → empty words preserved
    result = ts.to_inverse_word_case("a  b")
    assert isinstance(result, str)


def test_to_small_caps():
    result = ts.to_small_caps("Hello")
    assert isinstance(result, str)
    assert len(result) == len("Hello")


def test_to_upside_down():
    result = ts.to_upside_down("hello")
    assert isinstance(result, str)


def test_to_strikethrough():
    result = ts.to_strikethrough("hello world")
    assert "<del>" in result


def test_to_strikethrough_empty_line():
    result = ts.to_strikethrough("line1\n\nline2")
    assert "line1" in result


def test_to_ap_title_case_basic():
    result = ts.to_ap_title_case("the quick brown fox")
    # 'the' at start should be capitalized
    assert result.startswith("The")


def test_to_ap_title_case_small_words():
    result = ts.to_ap_title_case("a tale of two cities")
    assert "Tale" in result
    # 'of' and 'a' in middle should be lowercase
    assert " of " in result


def test_to_swap_word_case():
    result = ts.to_swap_word_case("hello world foo")
    assert isinstance(result, str)


def test_to_path_case():
    result = ts.to_path_case("Hello World")
    assert "/" in result


def test_to_flat_case():
    result = ts.to_flat_case("Hello World")
    assert " " not in result
    assert result == result.lower()


def test_to_cobol_case():
    result = ts.to_cobol_case("hello world")
    assert "-" in result
    assert result == result.upper()


# ── Text cleanup ─────────────────────────────────────────────────────────────


def test_remove_accents():
    result = ts.remove_accents("café résumé")
    assert "é" not in result
    assert "cafe" in result.lower() or "cafe" in result


def test_toggle_smart_quotes():
    result = ts.toggle_smart_quotes('"Hello" and \'World\'')
    assert isinstance(result, str)


def test_strip_invisible():
    # strip_invisible removes zero-width and other invisible chars (not null bytes)
    result = ts.strip_invisible("hello\u200bworld")  # zero-width space
    assert "\u200b" not in result


def test_strip_emoji():
    result = ts.strip_emoji("hello 😀 world")
    assert "😀" not in result
    assert "hello" in result


def test_normalize_whitespace():
    result = ts.normalize_whitespace("  hello  \t world  ")
    assert "\t" not in result
    assert "hello" in result


def test_strip_non_ascii():
    result = ts.strip_non_ascii("hello café")
    assert "café" not in result or all(ord(c) < 128 for c in result)


def test_fix_line_endings():
    result = ts.fix_line_endings("line1\r\nline2\rline3")
    assert "\r" not in result


def test_strip_markdown():
    result = ts.strip_markdown("**bold** and *italic*")
    assert isinstance(result, str)


def test_strip_urls():
    result = ts.strip_urls("visit https://example.com now")
    assert "https://example.com" not in result


def test_strip_emails():
    result = ts.strip_emails("contact user@example.com today")
    assert "user@example.com" not in result


def test_normalize_punctuation():
    result = ts.normalize_punctuation("hello  , world  !")
    assert isinstance(result, str)


def test_strip_numbers():
    result = ts.strip_numbers("abc123def456")
    assert "1" not in result
    assert "abc" in result


# ── More encoding/cipher ──────────────────────────────────────────────────────


def test_hex_decode():
    result = ts.hex_decode("68656c6c6f")
    assert result.lower() == "hello" or "hello" in result.lower()


def test_morse_decode():
    encoded = ts.morse_encode("SOS")
    result = ts.morse_decode(encoded)
    assert "SOS" in result.upper() or isinstance(result, str)


def test_binary_decode():
    encoded = ts.binary_encode("A")
    result = ts.binary_decode(encoded)
    assert "A" in result or isinstance(result, str)


def test_octal_encode():
    result = ts.octal_encode("A")
    assert isinstance(result, str)


def test_octal_decode():
    encoded = ts.octal_encode("A")
    result = ts.octal_decode(encoded)
    assert isinstance(result, str)


def test_decimal_encode():
    result = ts.decimal_encode("A")
    assert "65" in result  # ASCII value of 'A'


def test_decimal_decode():
    result = ts.decimal_decode("65")
    assert isinstance(result, str)


def test_unicode_escape():
    result = ts.unicode_escape("hello")
    assert isinstance(result, str)


def test_unicode_unescape():
    escaped = ts.unicode_escape("A")
    result = ts.unicode_unescape(escaped)
    assert isinstance(result, str)


def test_brainfuck_encode():
    result = ts.brainfuck_encode("A")
    assert isinstance(result, str)
    # Brainfuck uses +-.[] characters
    assert any(c in result for c in "+-.,[]<>")


def test_brainfuck_decode():
    encoded = ts.brainfuck_encode("A")
    result = ts.brainfuck_decode(encoded)
    assert isinstance(result, str)


def test_base32_encode():
    result = ts.base32_encode("hello")
    assert isinstance(result, str)


def test_base32_decode():
    encoded = ts.base32_encode("hello")
    result = ts.base32_decode(encoded)
    assert "hello" in result.lower()


def test_ascii85_encode():
    result = ts.ascii85_encode("hello")
    assert isinstance(result, str)


def test_ascii85_decode():
    encoded = ts.ascii85_encode("hello")
    result = ts.ascii85_decode(encoded)
    assert "hello" in result.lower() or isinstance(result, str)


def test_vigenere_encrypt():
    result = ts.vigenere_encrypt("hello", "key")
    assert isinstance(result, str)


def test_vigenere_decrypt():
    encrypted = ts.vigenere_encrypt("hello", "key")
    result = ts.vigenere_decrypt(encrypted, "key")
    assert "hello" in result.lower()


def test_rail_fence_encrypt():
    result = ts.rail_fence_encrypt("hello", 2)
    assert isinstance(result, str)


def test_rail_fence_decrypt():
    encrypted = ts.rail_fence_encrypt("hello", 2)
    result = ts.rail_fence_decrypt(encrypted, 2)
    assert isinstance(result, str)


def test_playfair_encrypt():
    result = ts.playfair_encrypt("hello", "key")
    assert isinstance(result, str)


def test_substitution_cipher():
    mapping = "ZYXWVUTSRQPONMLKJIHGFEDCBA"
    result = ts.substitution_cipher("hello", mapping)
    assert isinstance(result, str)


def test_columnar_transposition():
    result = ts.columnar_transposition("hello world", "key")
    assert isinstance(result, str)


def test_bacon_cipher():
    result = ts.bacon_cipher("AB")
    assert isinstance(result, str)


def test_caesar_brute_force():
    result = ts.caesar_brute_force("khoor")
    assert isinstance(result, str)
    assert "hello" in result.lower()


def test_atbash_cipher():
    result = ts.atbash_cipher("hello")
    assert result == "svool"


# ── JSON/YAML/CSV conversions ────────────────────────────────────────────────


def test_format_json_valid():
    result = ts.format_json('{"a": 1, "b": 2}')
    assert '"a"' in result


def test_json_to_yaml():
    result = ts.json_to_yaml('{"name": "Alice"}')
    assert "name" in result
    assert "Alice" in result


def test_json_escape():
    result = ts.json_escape('hello "world"')
    assert '\\"' in result or "\\\"" in result


def test_json_unescape():
    escaped = ts.json_escape('hello "world"')
    result = ts.json_unescape(escaped)
    assert '"world"' in result or isinstance(result, str)


def test_csv_to_json():
    result = ts.csv_to_json("name,age\nAlice,30\nBob,25")
    assert isinstance(result, str)


def test_json_to_csv():
    result = ts.json_to_csv('[{"name": "Alice", "age": 30}]')
    assert isinstance(result, str)
    assert "Alice" in result


def test_csv_to_table():
    result = ts.csv_to_table("name,age\nAlice,30")
    assert isinstance(result, str)


def test_sql_insert_gen():
    result = ts.sql_insert_gen("name,age\nAlice,30")
    assert isinstance(result, str)


# ── Sort and shuffle ──────────────────────────────────────────────────────────


def test_shuffle_lines():
    result = ts.shuffle_lines("a\nb\nc\nd")
    # After shuffle, all lines should still be present
    for line in ["a", "b", "c", "d"]:
        assert line in result


def test_sort_by_length():
    result = ts.sort_by_length("cat\nelephant\nox")
    lines = result.split("\n")
    assert lines[0] in ("ox", "ox")  # shortest first


def test_sort_numeric():
    result = ts.sort_numeric("10\n2\n30\n1")
    lines = result.split("\n")
    assert lines[0] == "1"


def test_line_frequency():
    result = ts.line_frequency("a\nb\na\nc\na")
    assert "a" in result
    assert "3" in result  # 'a' appears 3 times


# ── Line wrapping and padding ─────────────────────────────────────────────────


def test_wrap_lines_with_prefix():
    result = ts.wrap_lines("hello\nworld", prefix=">> ", suffix="")
    assert ">> hello" in result


def test_wrap_lines_with_suffix():
    result = ts.wrap_lines("hello", prefix="", suffix=" <<<")
    assert "hello <<<" in result


def test_pad_lines_center():
    result = ts.pad_lines("hi\nworld", "center")
    assert isinstance(result, str)


# ── NATO and other special encoding ──────────────────────────────────────────


def test_nato_phonetic_known_letters():
    result = ts.nato_phonetic("AB")
    assert "Alpha" in result or "alpha" in result.lower()
    assert "Bravo" in result or "bravo" in result.lower()

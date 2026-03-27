"""
Text transformations — pure functions, no I/O or side effects.

Keeps endpoint handlers thin and makes the logic easily testable.
"""

import base64
import codecs
import csv
import html
import io
import json
import re
import unicodedata
from urllib.parse import quote, unquote

import yaml


# ── Case transformations ──────────────────────────────────────────────────

def to_uppercase(text: str) -> str:
    return text.upper()

def to_lowercase(text: str) -> str:
    return text.lower()

def to_inverse_case(text: str) -> str:
    return "".join(
        c.lower() if c.isupper() else c.upper() for c in text
    )

def to_sentence_case(text: str) -> str:
    text = text.strip()
    if text.endswith("."):
        text = text[:-1]
    sentences = re.split(r"[.?]\s*(?=\S|$)|\n", text)
    result = ". ".join(
        s.strip().capitalize() for s in sentences if s.strip()
    )
    return result + "."

def to_title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.split())

def to_upper_camel_case(text: str) -> str:
    return "".join(w.capitalize() for w in text.split())

def to_lower_camel_case(text: str) -> str:
    pascal = to_upper_camel_case(text)
    return pascal[0].lower() + pascal[1:] if pascal else pascal

def to_snake_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.strip('_').lower()

def to_kebab_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s)
    return s.strip('-').lower()

def to_capitalize_words(text: str) -> str:
    return " ".join(w[0].upper() + w[1:] if w else w for w in text.split(" "))

def to_alternating_case(text: str) -> str:
    result = []
    i = 0
    for c in text:
        if c.isalpha():
            result.append(c.lower() if i % 2 == 0 else c.upper())
            i += 1
        else:
            result.append(c)
    return "".join(result)

def to_inverse_word_case(text: str) -> str:
    result = []
    for word in text.split(" "):
        if word:
            result.append(word[:-1].lower() + word[-1].upper() if len(word) > 1 else word.upper())
        else:
            result.append(word)
    return " ".join(result)

def to_wide_text(text: str) -> str:
    return " ".join(text)

_SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
)

def to_small_caps(text: str) -> str:
    return text.lower().translate(_SMALL_CAPS_MAP)

_UPSIDE_DOWN_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'\"",
    "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz∀qƆpƎℲפHIſʞ˥WNOԀQɹS┴∩ΛMX⅄Z0ƖᄅƐㄣϛ9ㄥ86˙'¡¿,„",
)

def to_upside_down(text: str) -> str:
    return text.translate(_UPSIDE_DOWN_MAP)[::-1]

def to_strikethrough(text: str) -> str:
    lines = text.split('\n')
    return '\n'.join(f'<del>{line}</del>' if line.strip() else line for line in lines)

# AP-style small words that should stay lowercase in titles
_AP_SMALL_WORDS = {
    'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in',
    'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet', 'is',
    'it', 'its', 'my', 'vs', 'via',
}

def to_ap_title_case(text: str) -> str:
    words = text.split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or i == len(words) - 1 or w.lower() not in _AP_SMALL_WORDS:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)

def to_swap_word_case(text: str) -> str:
    words = text.split(" ")
    result = []
    for i, w in enumerate(words):
        result.append(w.upper() if i % 2 == 0 else w.lower())
    return " ".join(result)

def to_dot_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1.\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '.', s)
    return s.strip('.').lower()

def to_constant_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.strip('_').upper()

def to_train_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
    words = re.split(r'[^a-zA-Z0-9]+', s)
    return "-".join(w.capitalize() for w in words if w)

def to_path_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1/\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '/', s)
    return s.strip('/').lower()

def to_flat_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '', s)
    return s.lower()

def to_cobol_case(text: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s)
    return s.strip('-').upper()

# ── Whitespace operations ─────────────────────────────────────────────────

def remove_extra_spaces(text: str) -> str:
    return " ".join(text.split())

def remove_all_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)

def remove_line_breaks(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text).strip()

# ── Text Cleaning ────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    from html.parser import HTMLParser
    from io import StringIO

    class _TagStripper(HTMLParser):
        _skip = frozenset(('head', 'style', 'script', 'noscript'))

        def __init__(self):
            super().__init__()
            self._fed: list[str] = []
            self._skip_depth = 0

        def handle_starttag(self, tag: str, attrs: list) -> None:
            if tag.lower() in self._skip:
                self._skip_depth += 1

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() in self._skip and self._skip_depth > 0:
                self._skip_depth -= 1

        def handle_data(self, data: str) -> None:
            if self._skip_depth == 0:
                self._fed.append(data)

        def get_text(self) -> str:
            return ''.join(self._fed)

    stripper = _TagStripper()
    stripper.feed(text)
    clean = html.unescape(stripper.get_text())
    clean = re.sub(r'\n\s*\n+', '\n\n', clean).strip()
    return clean

def remove_accents(text: str) -> str:
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def toggle_smart_quotes(text: str) -> str:
    has_smart = any(c in text for c in '\u2018\u2019\u201C\u201D')
    if has_smart:
        for smart, straight in {
            '\u2018': "'", '\u2019': "'",
            '\u201C': '"', '\u201D': '"',
            '\u2013': '-', '\u2014': '--',
            '\u2026': '...',
        }.items():
            text = text.replace(smart, straight)
    else:
        result = []
        open_double = True
        for ch in text:
            if ch == '"':
                result.append('\u201C' if open_double else '\u201D')
                open_double = not open_double
            else:
                result.append(ch)
        text = ''.join(result)
        result = []
        open_single = True
        for i, ch in enumerate(text):
            if ch == "'":
                if i > 0 and i < len(text) - 1 and text[i-1].isalpha() and text[i+1].isalpha():
                    result.append('\u2019')
                else:
                    result.append('\u2018' if open_single else '\u2019')
                    open_single = not open_single
            else:
                result.append(ch)
        text = ''.join(result)
        text = text.replace('...', '\u2026')
        text = re.sub(r'(?<!-)--(?!-)', '\u2014', text)
    return text

# ── Encoding ──────────────────────────────────────────────────────────────

def base64_encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def base64_decode(text: str) -> str:
    return base64.b64decode(text.encode("utf-8")).decode("utf-8")

def url_encode(text: str) -> str:
    return quote(text, safe="")

def url_decode(text: str) -> str:
    return unquote(text)

def hex_encode(text: str) -> str:
    return text.encode("utf-8").hex()

def hex_decode(text: str) -> str:
    return bytes.fromhex(text.strip()).decode("utf-8")

# ── Morse Code ─────────────────────────────────────────────────────────────

_MORSE_MAP = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', '.': '.-.-.-', ',': '--..--', '?': '..--..',
    "'": '.----.', '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-',
    '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.',
    '-': '-....-', '_': '..--.-', '"': '.-..-.', '$': '...-..-', '@': '.--.-.',
}
_MORSE_REVERSE = {v: k for k, v in _MORSE_MAP.items()}

def morse_encode(text: str) -> str:
    result = []
    for ch in text.upper():
        if ch == ' ':
            result.append('/')
        elif ch in _MORSE_MAP:
            result.append(_MORSE_MAP[ch])
    return ' '.join(result)

def morse_decode(text: str) -> str:
    words = text.strip().split(' / ')
    decoded = []
    for word in words:
        letters = word.strip().split()
        decoded.append(''.join(_MORSE_REVERSE.get(c, '') for c in letters))
    return ' '.join(decoded)

# ── Text Tools ────────────────────────────────────────────────────────────

def reverse_text(text: str) -> str:
    return text[::-1]

def sort_lines_asc(text: str) -> str:
    return "\n".join(sorted(text.splitlines(), key=str.casefold))

def sort_lines_desc(text: str) -> str:
    return "\n".join(sorted(text.splitlines(), key=str.casefold, reverse=True))

def reverse_lines(text: str) -> str:
    return "\n".join(text.splitlines()[::-1])

def number_lines(text: str) -> str:
    return "\n".join(f"{i}. {line}" for i, line in enumerate(text.splitlines(), 1))

def rot13(text: str) -> str:
    return codecs.encode(text, 'rot_13')

def remove_duplicate_lines(text: str) -> str:
    seen: set = set()
    result = []
    for line in text.splitlines():
        if line not in seen:
            seen.add(line)
            result.append(line)
    return "\n".join(result)

# ── Developer Tools ───────────────────────────────────────────────────────

def format_json(text: str) -> str:
    return json.dumps(json.loads(text), indent=2, ensure_ascii=False)

def json_to_yaml(text: str) -> str:
    return yaml.dump(json.loads(text), allow_unicode=True, default_flow_style=False)

# ── Escape / Unescape ────────────────────────────────────────────────────

def json_escape(text: str) -> str:
    return json.dumps(text)[1:-1]

def json_unescape(text: str) -> str:
    return json.loads('"' + text + '"')

def html_escape_text(text: str) -> str:
    return html.escape(text, quote=True)

def html_unescape_text(text: str) -> str:
    return html.unescape(text)

# ── CSV / JSON Conversion ────────────────────────────────────────────────

def csv_to_json(text: str) -> str:
    reader = csv.DictReader(io.StringIO(text))
    return json.dumps(list(reader), indent=2, ensure_ascii=False)

def json_to_csv(text: str) -> str:
    data = json.loads(text)
    if not isinstance(data, list) or not data:
        raise ValueError("Input must be a non-empty JSON array")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

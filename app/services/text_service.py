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

# ── Text Cleanup ──────────────────────────────────────────────────────────

def remove_extra_spaces(text: str) -> str:
    return " ".join(text.split())

def remove_all_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)

def remove_line_breaks(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text).strip()


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

def strip_invisible(text: str) -> str:
    return ''.join(c for c in text if unicodedata.category(c) != 'Cf')

def strip_emoji(text: str) -> str:
    import emoji
    cleaned = emoji.replace_emoji(text, replace='')
    return re.sub(r'  +', ' ', cleaned).strip()

def normalize_whitespace(text: str) -> str:
    return re.sub(r'[^\S\n]+', ' ', text)

def strip_non_ascii(text: str) -> str:
    return re.sub(r'[^\x00-\x7F]', '', text)

def fix_line_endings(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')

def strip_markdown(text: str) -> str:
    s = text
    s = re.sub(r'^#{1,6}\s+', '', s, flags=re.MULTILINE)
    s = re.sub(r'\!\[([^\]]*)\]\([^\)]+\)', r'\1', s)
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    s = re.sub(r'(\*\*|__)(.*?)\1', r'\2', s)
    s = re.sub(r'(\*|_)(.*?)\1', r'\2', s)
    s = re.sub(r'~~(.*?)~~', r'\1', s)
    s = re.sub(r'`{3}[\s\S]*?`{3}', '', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    s = re.sub(r'^>\s?', '', s, flags=re.MULTILINE)
    s = re.sub(r'^[-*+]\s+', '', s, flags=re.MULTILINE)
    s = re.sub(r'^\d+\.\s+', '', s, flags=re.MULTILINE)
    s = re.sub(r'^[-*_]{3,}\s*$', '', s, flags=re.MULTILINE)
    return s.strip()

def trim_lines(text: str) -> str:
    return '\n'.join(line.strip() for line in text.splitlines())

def strip_empty_lines(text: str) -> str:
    return '\n'.join(line for line in text.splitlines() if line.strip())

def strip_urls(text: str) -> str:
    s = re.sub(r'https?://\S+', '', text)
    s = re.sub(r'www\.\S+', '', s)
    return re.sub(r'  +', ' ', s).strip()

def strip_emails(text: str) -> str:
    s = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '', text)
    return re.sub(r'  +', ' ', s).strip()

def normalize_punctuation(text: str) -> str:
    s = re.sub(r'\s+([.,;:!?])', r'\1', text)
    s = re.sub(r'([.,;:!?])([^\s.,;:!?\'\"\)\]\}0-9])', r'\1 \2', s)
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'\s+\)', ')', s)
    s = re.sub(r'\.{2}(?!\.)', '.', s)
    return s

def strip_numbers(text: str) -> str:
    s = re.sub(r'\d+', '', text)
    return re.sub(r'  +', ' ', s).strip()

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


def shuffle_lines(text: str) -> str:
    import random
    lines = text.splitlines()
    random.shuffle(lines)
    return "\n".join(lines)


def sort_by_length(text: str) -> str:
    return "\n".join(sorted(text.splitlines(), key=len))


def sort_numeric(text: str) -> str:
    def _numeric_key(line: str):
        match = re.search(r'-?\d+\.?\d*', line)
        return float(match.group()) if match else float('inf')
    return "\n".join(sorted(text.splitlines(), key=_numeric_key))


def line_frequency(text: str) -> str:
    from collections import Counter
    counts = Counter(text.splitlines())
    return "\n".join(f"{count}x  {line}" for line, count in counts.most_common())



def split_to_lines(text: str, delimiter: str = ",") -> str:
    return "\n".join(part.strip() for part in text.split(delimiter))


def join_lines(text: str, separator: str = ", ") -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return separator.join(lines)


def pad_lines(text: str, align: str = "left") -> str:
    lines = text.splitlines()
    max_len = max((len(line) for line in lines), default=0)
    if align == "right":
        return "\n".join(line.rjust(max_len) for line in lines)
    elif align == "center":
        return "\n".join(line.center(max_len) for line in lines)
    return "\n".join(line.ljust(max_len) for line in lines)


def wrap_lines(text: str, prefix: str = "", suffix: str = "") -> str:
    return "\n".join(f"{prefix}{line}{suffix}" for line in text.splitlines())


def _line_matches(line: str, pattern: str, case_sensitive: bool, use_regex: bool) -> bool:
    if use_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return bool(re.search(pattern, line, flags))
        except re.error:
            return False
    if case_sensitive:
        return pattern in line
    return pattern.lower() in line.lower()


def filter_lines_contain(text: str, pattern: str, case_sensitive: bool = False, use_regex: bool = False) -> str:
    return "\n".join(line for line in text.splitlines() if _line_matches(line, pattern, case_sensitive, use_regex))


def remove_lines_contain(text: str, pattern: str, case_sensitive: bool = False, use_regex: bool = False) -> str:
    return "\n".join(line for line in text.splitlines() if not _line_matches(line, pattern, case_sensitive, use_regex))


def truncate_lines(text: str, max_length: int = 80) -> str:
    result = []
    for line in text.splitlines():
        if len(line) > max_length:
            result.append(line[:max_length - 1] + "…")
        else:
            result.append(line)
    return "\n".join(result)


def extract_nth_lines(text: str, n: int = 2, offset: int = 0) -> str:
    lines = text.splitlines()
    return "\n".join(lines[i] for i in range(offset, len(lines), n))

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

"""
TextService — pure business logic for text transformations.

All methods are static; no I/O or side effects.
Keeps endpoint handlers thin and makes the logic easily testable.
"""

import base64
import json
import re
from urllib.parse import quote, unquote

import yaml


class TextService:

    # ── Case transformations ──────────────────────────────────────────────────

    @staticmethod
    def to_uppercase(text: str) -> str:
        return text.upper()

    @staticmethod
    def to_lowercase(text: str) -> str:
        return text.lower()

    @staticmethod
    def to_inverse_case(text: str) -> str:
        return "".join(
            c.lower() if c.isupper() else c.upper() for c in text
        )

    @staticmethod
    def to_sentence_case(text: str) -> str:
        text = text.strip()
        if text.endswith("."):
            text = text[:-1]
        sentences = re.split(r"[.?]\s*(?=\S|$)|\n", text)
        result = ". ".join(
            s.strip().capitalize() for s in sentences if s.strip()
        )
        return result + "."

    @staticmethod
    def to_title_case(text: str) -> str:
        return " ".join(w.capitalize() for w in text.split())

    @staticmethod
    def to_upper_camel_case(text: str) -> str:
        return "".join(w.capitalize() for w in text.split())

    @staticmethod
    def to_lower_camel_case(text: str) -> str:
        pascal = TextService.to_upper_camel_case(text)
        return pascal[0].lower() + pascal[1:] if pascal else pascal

    # ── Whitespace operations ─────────────────────────────────────────────────

    @staticmethod
    def remove_extra_spaces(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def remove_all_spaces(text: str) -> str:
        return re.sub(r"\s+", "", text)

    @staticmethod
    def remove_line_breaks(text: str) -> str:
        return re.sub(r"[\r\n]+", " ", text).strip()

    @staticmethod
    def minify(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    # ── Encoding ──────────────────────────────────────────────────────────────

    @staticmethod
    def base64_encode(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def base64_decode(text: str) -> str:
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def url_encode(text: str) -> str:
        return quote(text, safe="")

    @staticmethod
    def url_decode(text: str) -> str:
        return unquote(text)

    # ── Text Tools ────────────────────────────────────────────────────────────

    @staticmethod
    def reverse_text(text: str) -> str:
        return text[::-1]

    @staticmethod
    def sort_lines_asc(text: str) -> str:
        lines = text.splitlines()
        return "\n".join(sorted(lines, key=str.casefold))

    @staticmethod
    def sort_lines_desc(text: str) -> str:
        lines = text.splitlines()
        return "\n".join(sorted(lines, key=str.casefold, reverse=True))

    @staticmethod
    def remove_duplicate_lines(text: str) -> str:
        seen: set = set()
        result = []
        for line in text.splitlines():
            if line not in seen:
                seen.add(line)
                result.append(line)
        return "\n".join(result)

    # ── Developer Tools ───────────────────────────────────────────────────────

    @staticmethod
    def format_json(text: str) -> str:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)

    @staticmethod
    def json_to_yaml(text: str) -> str:
        return yaml.dump(json.loads(text), allow_unicode=True, default_flow_style=False)


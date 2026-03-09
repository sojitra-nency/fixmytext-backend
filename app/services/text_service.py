"""
TextService — pure business logic for text transformations.

All methods are static; no I/O or side effects.
Keeps endpoint handlers thin and makes the logic easily testable.
"""

import re


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


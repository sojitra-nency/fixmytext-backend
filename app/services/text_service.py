"""
TextService — pure business logic for text transformations.

All methods are static; no I/O or side effects.
Keeps endpoint handlers thin and makes the logic easily testable.
"""

import re


class TextService:
    WORDS_PER_MINUTE = 125

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

    # ── Analysis ──────────────────────────────────────────────────────────────

    @staticmethod
    def analyze(text: str) -> dict:
        words = [w for w in text.split() if w]
        sentences = [
            s for s in re.split(r"[.?]\s*(?=\S|$)|\n", text) if s.strip()
        ]
        return {
            "text": text,
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": len(text),
            "character_count_no_spaces": len(text.replace(" ", "")),
            "reading_time_minutes": round(
                len(words) / TextService.WORDS_PER_MINUTE, 2
            ),
        }

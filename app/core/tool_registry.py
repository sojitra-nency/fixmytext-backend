"""
Tool registry -- single source of truth for all text transformation tools.

Each tool is registered with its ID, handler, type (local/ai), display name,
category, and optional error-handling metadata.  Adding a new tool requires
only adding an entry in ``_register_all_tools()`` below; the endpoint layer
and OpenAPI docs are derived automatically.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


class ToolType(StrEnum):
    """Whether a tool runs locally or calls an AI API."""

    LOCAL = "local"
    AI = "ai"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Immutable definition of a single text transformation tool.

    Attributes:
        id: URL-safe slug used as the route path (e.g. ``"uppercase"``).
        handler: For LOCAL tools this is the sync function from
            ``text_service``; for AI tools it is ``None`` (the endpoint
            dispatches via ``ai_service.run_ai_tool``).
        tool_type: LOCAL or AI.
        display_name: Human-readable label shown in OpenAPI docs.
        category: Grouping tag for the sidebar / OpenAPI tags.
        error_detail: Optional custom 400-level message for decode/parse
            tools that can raise on bad input.
        error_exceptions: Tuple of exception types that should be caught
            and surfaced as 400 errors.
        request_model: Name of the *non-standard* request schema when the
            tool needs more than ``TextRequest`` (e.g. ``"CaesarRequest"``).
            ``None`` means the tool uses the default ``TextRequest``.
        requires_auth: If ``True`` the route uses ``get_current_user``
            instead of ``get_optional_user`` (all AI tools).
    """

    id: str
    handler: Callable | None
    tool_type: ToolType
    display_name: str
    category: str = "general"
    error_detail: str | None = None
    error_exceptions: tuple[type[Exception], ...] = ()
    request_model: str | None = None
    requires_auth: bool = False


# ---------------------------------------------------------------------------
# Internal registry dict -- populated at import time
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def get_tool(tool_id: str) -> ToolDefinition | None:
    """Look up a tool by ID.  Returns ``None`` if not found."""
    return _TOOL_REGISTRY.get(tool_id)


def get_all_tools() -> dict[str, ToolDefinition]:
    """Return a *shallow copy* of the full tool registry."""
    return dict(_TOOL_REGISTRY)


def _register(
    tool_id: str,
    handler: Callable | None,
    tool_type: ToolType,
    display_name: str,
    category: str = "general",
    *,
    error_detail: str | None = None,
    error_exceptions: tuple[type[Exception], ...] = (),
    request_model: str | None = None,
    requires_auth: bool = False,
) -> None:
    """Register a tool.  Called at module-init time only."""
    _TOOL_REGISTRY[tool_id] = ToolDefinition(
        id=tool_id,
        handler=handler,
        tool_type=tool_type,
        display_name=display_name,
        category=category,
        error_detail=error_detail,
        error_exceptions=error_exceptions,
        request_model=request_model,
        requires_auth=requires_auth,
    )


# ---------------------------------------------------------------------------
# Registration of every tool
# ---------------------------------------------------------------------------


def _register_all_tools() -> None:  # noqa: C901 -- unavoidably long
    """Register every tool that currently has an endpoint.

    The order here mirrors the original ``text.py`` endpoint order so that
    OpenAPI documentation keeps a familiar layout.
    """
    import binascii

    from app.services import text_service as ts

    L = ToolType.LOCAL  # shorthand
    A = ToolType.AI

    # ── Case transformations ────────────────────────────────────────────
    _register("uppercase", ts.to_uppercase, L, "Uppercase", "case")
    _register("lowercase", ts.to_lowercase, L, "Lowercase", "case")
    _register("inversecase", ts.to_inverse_case, L, "Inverse Case", "case")
    _register("sentencecase", ts.to_sentence_case, L, "Sentence Case", "case")
    _register("titlecase", ts.to_title_case, L, "Title Case", "case")
    _register(
        "upper-camel-case",
        ts.to_upper_camel_case,
        L,
        "UpperCamelCase",
        "case",
    )
    _register(
        "lower-camel-case",
        ts.to_lower_camel_case,
        L,
        "lowerCamelCase",
        "case",
    )
    _register("snake-case", ts.to_snake_case, L, "snake_case", "case")
    _register("kebab-case", ts.to_kebab_case, L, "kebab-case", "case")
    _register(
        "capitalize-words",
        ts.to_capitalize_words,
        L,
        "Capitalize Words",
        "case",
    )
    _register(
        "alternating-case",
        ts.to_alternating_case,
        L,
        "aLtErNaTiNg CaSe",
        "case",
    )
    _register(
        "inverse-word-case",
        ts.to_inverse_word_case,
        L,
        "Inverse Word Case",
        "case",
    )
    _register("wide-text", ts.to_wide_text, L, "W i d e  Text", "case")
    _register("small-caps", ts.to_small_caps, L, "Small Caps", "case")
    _register("upside-down", ts.to_upside_down, L, "Upside Down", "case")
    _register("strikethrough", ts.to_strikethrough, L, "Strikethrough", "case")
    _register("ap-title-case", ts.to_ap_title_case, L, "AP Title Case", "case")
    _register("swap-word-case", ts.to_swap_word_case, L, "Swap Word Case", "case")
    _register("dot-case", ts.to_dot_case, L, "dot.case", "case")
    _register("constant-case", ts.to_constant_case, L, "CONSTANT_CASE", "case")
    _register("train-case", ts.to_train_case, L, "Train-Case", "case")
    _register("path-case", ts.to_path_case, L, "path/case", "case")
    _register("flat-case", ts.to_flat_case, L, "flatcase", "case")
    _register("cobol-case", ts.to_cobol_case, L, "COBOL-CASE", "case")

    # ── Text cleanup / whitespace ───────────────────────────────────────
    _register(
        "remove-extra-spaces",
        ts.remove_extra_spaces,
        L,
        "Remove Extra Spaces",
        "cleanup",
    )
    _register(
        "remove-all-spaces",
        ts.remove_all_spaces,
        L,
        "Remove All Spaces",
        "cleanup",
    )
    _register(
        "remove-line-breaks",
        ts.remove_line_breaks,
        L,
        "Remove Line Breaks",
        "cleanup",
    )

    # ── Text cleaning ───────────────────────────────────────────────────
    _register("strip-html", ts.strip_html, L, "Strip HTML", "cleaning")
    _register("remove-accents", ts.remove_accents, L, "Remove Accents", "cleaning")
    _register(
        "toggle-smart-quotes",
        ts.toggle_smart_quotes,
        L,
        "Toggle Smart Quotes",
        "cleaning",
    )
    _register("strip-invisible", ts.strip_invisible, L, "Strip Invisible", "cleaning")
    _register("strip-emoji", ts.strip_emoji, L, "Strip Emoji", "cleaning")
    _register(
        "normalize-whitespace",
        ts.normalize_whitespace,
        L,
        "Normalize Whitespace",
        "cleaning",
    )
    _register("strip-non-ascii", ts.strip_non_ascii, L, "Strip Non-ASCII", "cleaning")
    _register(
        "fix-line-endings",
        ts.fix_line_endings,
        L,
        "Fix Line Endings",
        "cleaning",
    )
    _register("strip-markdown", ts.strip_markdown, L, "Strip Markdown", "cleaning")
    _register("trim-lines", ts.trim_lines, L, "Trim Lines", "cleaning")
    _register(
        "strip-empty-lines",
        ts.strip_empty_lines,
        L,
        "Strip Empty Lines",
        "cleaning",
    )
    _register("strip-urls", ts.strip_urls, L, "Strip URLs", "cleaning")
    _register("strip-emails", ts.strip_emails, L, "Strip Emails", "cleaning")
    _register(
        "normalize-punctuation",
        ts.normalize_punctuation,
        L,
        "Normalize Punctuation",
        "cleaning",
    )
    _register("strip-numbers", ts.strip_numbers, L, "Strip Numbers", "cleaning")

    # ── Encoding ────────────────────────────────────────────────────────
    _register("base64-encode", ts.base64_encode, L, "Base64 Encode", "encoding")
    _register(
        "base64-decode",
        ts.base64_decode,
        L,
        "Base64 Decode",
        "encoding",
        error_detail="Invalid Base64 input",
        error_exceptions=(binascii.Error, UnicodeDecodeError, ValueError),
    )
    _register("url-encode", ts.url_encode, L, "URL Encode", "encoding")
    _register(
        "url-decode",
        ts.url_decode,
        L,
        "URL Decode",
        "encoding",
        error_detail="Invalid URL-encoded input",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )
    _register("hex-encode", ts.hex_encode, L, "Hex Encode", "encoding")
    _register(
        "hex-decode",
        ts.hex_decode,
        L,
        "Hex Decode",
        "encoding",
        error_detail="Invalid hexadecimal input",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )
    _register("morse-encode", ts.morse_encode, L, "Morse Encode", "encoding")
    _register(
        "morse-decode",
        ts.morse_decode,
        L,
        "Morse Decode",
        "encoding",
        error_detail="Invalid Morse code input",
        error_exceptions=(KeyError, ValueError),
    )

    # ── Binary / Octal / Decimal ────────────────────────────────────────
    _register("binary-encode", ts.binary_encode, L, "Binary Encode", "encoding")
    _register(
        "binary-decode",
        ts.binary_decode,
        L,
        "Binary Decode",
        "encoding",
        error_detail="Invalid binary input",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )
    _register("octal-encode", ts.octal_encode, L, "Octal Encode", "encoding")
    _register(
        "octal-decode",
        ts.octal_decode,
        L,
        "Octal Decode",
        "encoding",
        error_detail="Invalid octal input",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )
    _register("decimal-encode", ts.decimal_encode, L, "Decimal Encode", "encoding")
    _register(
        "decimal-decode",
        ts.decimal_decode,
        L,
        "Decimal Decode",
        "encoding",
        error_detail="Invalid decimal input",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )

    # ── Unicode Escape / Unescape ───────────────────────────────────────
    _register("unicode-escape", ts.unicode_escape, L, "Unicode Escape", "encoding")
    _register(
        "unicode-unescape",
        ts.unicode_unescape,
        L,
        "Unicode Unescape",
        "encoding",
        error_detail="Invalid Unicode escape sequence",
        error_exceptions=(ValueError, UnicodeDecodeError),
    )

    # ── Brainfuck ───────────────────────────────────────────────────────
    _register(
        "brainfuck-encode",
        ts.brainfuck_encode,
        L,
        "Brainfuck Encode",
        "encoding",
    )
    _register(
        "brainfuck-decode",
        ts.brainfuck_decode,
        L,
        "Brainfuck Decode",
        "encoding",
        error_detail="Brainfuck execution error",
        error_exceptions=(ValueError,),
    )

    # ── Ciphers ─────────────────────────────────────────────────────────
    _register("atbash", ts.atbash_cipher, L, "Atbash Cipher", "cipher")
    _register(
        "caesar-cipher",
        ts.caesar_cipher,
        L,
        "Caesar Cipher",
        "cipher",
        request_model="CaesarRequest",
    )
    _register(
        "caesar-brute-force",
        ts.caesar_brute_force,
        L,
        "Caesar Brute Force",
        "cipher",
    )
    _register(
        "vigenere-encrypt",
        ts.vigenere_encrypt,
        L,
        "Vigenere Encrypt",
        "cipher",
        request_model="KeyedCipherRequest",
        error_detail="Invalid key",
        error_exceptions=(ValueError,),
    )
    _register(
        "vigenere-decrypt",
        ts.vigenere_decrypt,
        L,
        "Vigenere Decrypt",
        "cipher",
        request_model="KeyedCipherRequest",
        error_detail="Invalid key",
        error_exceptions=(ValueError,),
    )
    _register(
        "rail-fence-encrypt",
        ts.rail_fence_encrypt,
        L,
        "Rail Fence Encrypt",
        "cipher",
        request_model="RailFenceRequest",
    )
    _register(
        "rail-fence-decrypt",
        ts.rail_fence_decrypt,
        L,
        "Rail Fence Decrypt",
        "cipher",
        request_model="RailFenceRequest",
    )
    _register(
        "playfair-encrypt",
        ts.playfair_encrypt,
        L,
        "Playfair Encrypt",
        "cipher",
        request_model="KeyedCipherRequest",
        error_detail="Invalid Playfair input",
        error_exceptions=(ValueError,),
    )
    _register(
        "substitution-cipher",
        ts.substitution_cipher,
        L,
        "Substitution Cipher",
        "cipher",
        request_model="SubstitutionRequest",
        error_detail="Invalid substitution mapping",
        error_exceptions=(ValueError,),
    )
    _register(
        "columnar-transposition",
        ts.columnar_transposition,
        L,
        "Columnar Transposition",
        "cipher",
        request_model="KeyedCipherRequest",
        error_detail="Invalid key",
        error_exceptions=(ValueError,),
    )
    _register("nato-phonetic", ts.nato_phonetic, L, "NATO Phonetic", "cipher")
    _register("bacon-cipher", ts.bacon_cipher, L, "Bacon Cipher", "cipher")

    # ── Encoding extensions ─────────────────────────────────────────────
    _register("base32-encode", ts.base32_encode, L, "Base32 Encode", "encoding")
    _register(
        "base32-decode",
        ts.base32_decode,
        L,
        "Base32 Decode",
        "encoding",
        error_detail="Invalid Base32 input",
        error_exceptions=(Exception,),
    )
    _register("ascii85-encode", ts.ascii85_encode, L, "Ascii85 Encode", "encoding")
    _register(
        "ascii85-decode",
        ts.ascii85_decode,
        L,
        "Ascii85 Decode",
        "encoding",
        error_detail="Invalid Ascii85 input",
        error_exceptions=(Exception,),
    )

    # ── Developer tools ─────────────────────────────────────────────────
    _register(
        "xml-to-json",
        ts.xml_to_json,
        L,
        "XML to JSON",
        "developer",
        error_detail="Invalid XML input",
        error_exceptions=(Exception,),
    )
    _register("csv-to-table", ts.csv_to_table, L, "CSV to Table", "developer")
    _register(
        "sql-insert-gen",
        ts.sql_insert_gen,
        L,
        "SQL INSERT Generator",
        "developer",
        error_detail="Invalid CSV input",
        error_exceptions=(ValueError,),
    )

    # ── Text tools ──────────────────────────────────────────────────────
    _register("reverse", ts.reverse_text, L, "Reverse Text", "text-tools")
    _register("sort-lines-asc", ts.sort_lines_asc, L, "Sort Lines A-Z", "text-tools")
    _register(
        "sort-lines-desc",
        ts.sort_lines_desc,
        L,
        "Sort Lines Z-A",
        "text-tools",
    )
    _register(
        "remove-duplicate-lines",
        ts.remove_duplicate_lines,
        L,
        "Remove Duplicate Lines",
        "text-tools",
    )
    _register("reverse-lines", ts.reverse_lines, L, "Reverse Lines", "text-tools")
    _register("number-lines", ts.number_lines, L, "Number Lines", "text-tools")
    _register("shuffle-lines", ts.shuffle_lines, L, "Shuffle Lines", "text-tools")
    _register("sort-by-length", ts.sort_by_length, L, "Sort by Length", "text-tools")
    _register("sort-numeric", ts.sort_numeric, L, "Sort Numeric", "text-tools")
    _register("line-frequency", ts.line_frequency, L, "Line Frequency", "text-tools")
    _register(
        "split-to-lines",
        ts.split_to_lines,
        L,
        "Split to Lines",
        "text-tools",
        request_model="SplitJoinRequest",
    )
    _register(
        "join-lines",
        ts.join_lines,
        L,
        "Join Lines",
        "text-tools",
        request_model="SplitJoinRequest",
    )
    _register(
        "pad-lines",
        ts.pad_lines,
        L,
        "Pad Lines",
        "text-tools",
        request_model="PadRequest",
    )
    _register(
        "wrap-lines",
        ts.wrap_lines,
        L,
        "Wrap Lines",
        "text-tools",
        request_model="WrapRequest",
    )
    _register(
        "filter-lines",
        ts.filter_lines_contain,
        L,
        "Filter Lines",
        "text-tools",
        request_model="FilterRequest",
    )
    _register(
        "remove-lines",
        ts.remove_lines_contain,
        L,
        "Remove Lines",
        "text-tools",
        request_model="FilterRequest",
    )
    _register(
        "truncate-lines",
        ts.truncate_lines,
        L,
        "Truncate Lines",
        "text-tools",
        request_model="TruncateRequest",
    )
    _register(
        "extract-nth-lines",
        ts.extract_nth_lines,
        L,
        "Extract Nth Lines",
        "text-tools",
        request_model="NthLineRequest",
    )
    _register("rot13", ts.rot13, L, "ROT13", "text-tools")

    # ── Developer tools (format / escape / convert) ─────────────────────
    _register(
        "format-json",
        ts.format_json,
        L,
        "Format JSON",
        "developer",
        error_detail="Invalid JSON input",
        error_exceptions=(Exception,),
    )
    _register(
        "json-to-yaml",
        ts.json_to_yaml,
        L,
        "JSON to YAML",
        "developer",
        error_detail="Invalid JSON input",
        error_exceptions=(Exception,),
    )
    _register("json-escape", ts.json_escape, L, "JSON Escape", "developer")
    _register(
        "json-unescape",
        ts.json_unescape,
        L,
        "JSON Unescape",
        "developer",
        error_detail="Invalid JSON escaped input",
        error_exceptions=(Exception,),
    )
    _register("html-escape", ts.html_escape_text, L, "HTML Escape", "developer")
    _register("html-unescape", ts.html_unescape_text, L, "HTML Unescape", "developer")
    _register(
        "csv-to-json",
        ts.csv_to_json,
        L,
        "CSV to JSON",
        "developer",
        error_detail="Invalid CSV input",
        error_exceptions=(Exception,),
    )
    _register(
        "json-to-csv",
        ts.json_to_csv,
        L,
        "JSON to CSV",
        "developer",
        error_detail="Invalid JSON input (expected array of objects)",
        error_exceptions=(Exception,),
    )

    # ── AI tools ────────────────────────────────────────────────────────
    # All AI tools: handler=None, requires_auth=True.  The endpoint layer
    # dispatches them through ``ai_service.run_ai_tool(tool_id, text)``.

    _register(
        "generate-hashtags",
        None,
        A,
        "Generate Hashtags",
        "ai",
        requires_auth=True,
    )
    _register(
        "generate-seo-titles",
        None,
        A,
        "Generate SEO Titles",
        "ai",
        requires_auth=True,
    )
    _register(
        "generate-meta-descriptions",
        None,
        A,
        "Generate Meta Descriptions",
        "ai",
        requires_auth=True,
    )
    _register(
        "generate-blog-outline",
        None,
        A,
        "Generate Blog Outline",
        "ai",
        requires_auth=True,
    )
    _register(
        "shorten-for-tweet",
        None,
        A,
        "Shorten for Tweet",
        "ai",
        requires_auth=True,
    )
    _register(
        "rewrite-email",
        None,
        A,
        "Rewrite Email",
        "ai",
        requires_auth=True,
    )
    _register(
        "extract-keywords",
        None,
        A,
        "Extract Keywords",
        "ai",
        requires_auth=True,
    )
    _register(
        "translate",
        None,
        A,
        "Translate",
        "ai",
        requires_auth=True,
        request_model="TranslateRequest",
    )
    _register(
        "transliterate",
        None,
        A,
        "Transliterate",
        "ai",
        requires_auth=True,
        request_model="TranslateRequest",
    )
    _register("emojify", None, A, "Emojify", "ai", requires_auth=True)
    _register(
        "detect-language",
        None,
        A,
        "Detect Language",
        "ai",
        requires_auth=True,
    )
    _register("summarize", None, A, "Summarize", "ai", requires_auth=True)
    _register("fix-grammar", None, A, "Fix Grammar", "ai", requires_auth=True)
    _register("paraphrase", None, A, "Paraphrase", "ai", requires_auth=True)
    _register(
        "change-tone",
        None,
        A,
        "Change Tone",
        "ai",
        requires_auth=True,
        request_model="ToneRequest",
    )
    _register(
        "analyze-sentiment",
        None,
        A,
        "Analyze Sentiment",
        "ai",
        requires_auth=True,
    )
    _register(
        "lengthen-text",
        None,
        A,
        "Lengthen Text",
        "ai",
        requires_auth=True,
    )
    _register("eli5", None, A, "ELI5", "ai", requires_auth=True)
    _register("proofread", None, A, "Proofread", "ai", requires_auth=True)
    _register(
        "generate-title",
        None,
        A,
        "Generate Title",
        "ai",
        requires_auth=True,
    )
    _register(
        "refactor-prompt",
        None,
        A,
        "Refactor Prompt",
        "ai",
        requires_auth=True,
    )
    _register(
        "change-format",
        None,
        A,
        "Change Format",
        "ai",
        requires_auth=True,
        request_model="FormatRequest",
    )

    # -- AI writing tools ------------------------------------------------
    _register(
        "academic-style",
        None,
        A,
        "Academic Style",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "creative-style",
        None,
        A,
        "Creative Style",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "technical-style",
        None,
        A,
        "Technical Style",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "active-voice",
        None,
        A,
        "Active Voice",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "redundancy-remover",
        None,
        A,
        "Redundancy Remover",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "sentence-splitter",
        None,
        A,
        "Sentence Splitter",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "conciseness",
        None,
        A,
        "Conciseness",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "resume-bullets",
        None,
        A,
        "Resume Bullets",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "meeting-notes",
        None,
        A,
        "Meeting Notes",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "cover-letter",
        None,
        A,
        "Cover Letter",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "outline-to-draft",
        None,
        A,
        "Outline to Draft",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "continue-writing",
        None,
        A,
        "Continue Writing",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "rewrite-unique",
        None,
        A,
        "Rewrite Unique",
        "ai-writing",
        requires_auth=True,
    )
    _register(
        "tone-analyzer",
        None,
        A,
        "Tone Analyzer",
        "ai-writing",
        requires_auth=True,
    )

    # -- AI content tools ------------------------------------------------
    _register(
        "linkedin-post",
        None,
        A,
        "LinkedIn Post",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "twitter-thread",
        None,
        A,
        "Twitter Thread",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "instagram-caption",
        None,
        A,
        "Instagram Caption",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "youtube-description",
        None,
        A,
        "YouTube Description",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "social-bio",
        None,
        A,
        "Social Bio",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "product-description",
        None,
        A,
        "Product Description",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "cta-generator",
        None,
        A,
        "CTA Generator",
        "ai-content",
        requires_auth=True,
    )
    _register("ad-copy", None, A, "Ad Copy", "ai-content", requires_auth=True)
    _register(
        "landing-headline",
        None,
        A,
        "Landing Headline",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "email-subject",
        None,
        A,
        "Email Subject",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "content-ideas",
        None,
        A,
        "Content Ideas",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "hook-generator",
        None,
        A,
        "Hook Generator",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "angle-generator",
        None,
        A,
        "Angle Generator",
        "ai-content",
        requires_auth=True,
    )
    _register(
        "faq-schema",
        None,
        A,
        "FAQ Schema",
        "ai-content",
        requires_auth=True,
    )

    # -- AI language tools -----------------------------------------------
    _register(
        "pos-tagger",
        None,
        A,
        "POS Tagger",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "sentence-type",
        None,
        A,
        "Sentence Type",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "grammar-explain",
        None,
        A,
        "Grammar Explain",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "synonym-finder",
        None,
        A,
        "Synonym Finder",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "antonym-finder",
        None,
        A,
        "Antonym Finder",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "define-words",
        None,
        A,
        "Define Words",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "word-power",
        None,
        A,
        "Word Power",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "vocab-complexity",
        None,
        A,
        "Vocab Complexity",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "jargon-simplifier",
        None,
        A,
        "Jargon Simplifier",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "formality-detector",
        None,
        A,
        "Formality Detector",
        "ai-language",
        requires_auth=True,
    )
    _register(
        "cliche-detector",
        None,
        A,
        "Cliche Detector",
        "ai-language",
        requires_auth=True,
    )

    # -- AI generator tools ----------------------------------------------
    _register(
        "regex-generator",
        None,
        A,
        "Regex Generator",
        "ai-generator",
        requires_auth=True,
    )
    _register(
        "writing-prompt",
        None,
        A,
        "Writing Prompt",
        "ai-generator",
        requires_auth=True,
    )
    _register(
        "team-name-generator",
        None,
        A,
        "Team Name Generator",
        "ai-generator",
        requires_auth=True,
    )
    _register(
        "mock-api-response",
        None,
        A,
        "Mock API Response",
        "ai-generator",
        requires_auth=True,
    )


# Run at module import time so the registry is populated before any
# endpoint handler accesses it.
_register_all_tools()

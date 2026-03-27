"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

import binascii
import json
import csv
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.text import TextRequest, TextResponse, TranslateRequest, ToneRequest, FormatRequest
from app.core.rate_limit import ai_limiter
from app.core.deps import get_current_user, get_optional_user
from app.db.session import get_db
from app.db.models import User
from app.services import text_service as ts

logger = logging.getLogger(__name__)
from app.services.pass_service import check_tool_access, check_visitor_access, record_tool_discovery
from app.services.ai_service import (
    HashtagService, SEOTitleService, MetaDescriptionService, BlogOutlineService,
    TweetShortenerService, EmailRewriterService,
    KeywordExtractorService, TranslatorService, TransliterationService,
    SummarizerService, GrammarFixerService,
    ParaphraserService, ToneChangerService, SentimentAnalyzerService,
    TextLengthenerService, FormatChangerService,
    ELI5Service, ProofreadService, TitleGeneratorService, PromptRefactorService,
    EmojifyService, LanguageDetector,
)

router = APIRouter(prefix="/text", tags=["Text"])


# ── Helper ────────────────────────────────────────────────────────────────────

async def _local_endpoint(request: Request, req: TextRequest, operation: str, transform_fn, user: User | None = None, db: AsyncSession | None = None) -> TextResponse:
    """Shared handler for non-AI text endpoints with optional usage tracking."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=%s user=%s ip=%s chars=%d", operation, user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, operation, "api", user, db)
    result = transform_fn(req.text)
    logger.info("LOCAL  op=%s -> OK (%d chars)", operation, len(result))
    return TextResponse(original=req.text, result=result, operation=operation)


async def _enforce_tool_access(request: Request, tool_id: str, tool_type: str, user: User | None, db: AsyncSession):
    """Unified tool access check — works for both authenticated and visitor users."""
    if user:
        result = await check_tool_access(user, tool_id, tool_type, db)
    else:
        fingerprint = request.headers.get("x-visitor-id", "")
        ip = request.client.host if request.client else ""
        result = await check_visitor_access(fingerprint, ip, tool_id, tool_type, db)

    if not result["allowed"]:
        logger.warning("ACCESS DENIED tool=%s type=%s user=%s reason=%s",
                        tool_id, tool_type,
                        str(user.id) if user else "visitor",
                        result.get("message", "limit reached"))
        raise HTTPException(status_code=429, detail=result.get("message", "Daily limit reached. Get a pass for more access!"))

    # Record tool discovery for authenticated users (fire-and-forget, ON CONFLICT DO NOTHING)
    if user:
        await record_tool_discovery(user.id, tool_id, db)


async def _ai_endpoint(request: Request, req, operation: str, service_fn, error_detail: str, *extra_args, user: User = None, db: AsyncSession = None) -> TextResponse:
    """Shared handler for all AI-powered endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("AI     op=%s user=%s ip=%s chars=%d", operation, user_id, client_ip, len(req.text))
    ai_limiter.check(request)
    if db:
        await _enforce_tool_access(request, operation, "ai", user, db)
    try:
        result = await service_fn(req.text, *extra_args)
        logger.info("AI     op=%s -> OK (%d chars)", operation, len(result))
        return TextResponse(original=req.text, result=result, operation=operation)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("AI     op=%s -> FAILED: %s", operation, exc)
        raise HTTPException(status_code=500, detail=error_detail)


# ── Text Transformations ─────────────────────────────────────────────────────

@router.post("/uppercase", response_model=TextResponse)
async def uppercase(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to UPPERCASE."""
    return await _local_endpoint(request, req, "uppercase", ts.to_uppercase, user, db)


@router.post("/lowercase", response_model=TextResponse)
async def lowercase(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to lowercase."""
    return await _local_endpoint(request, req, "lowercase", ts.to_lowercase, user, db)


@router.post("/inversecase", response_model=TextResponse)
async def inversecase(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Invert case of every character."""
    return await _local_endpoint(request, req, "inversecase", ts.to_inverse_case, user, db)


@router.post("/sentencecase", response_model=TextResponse)
async def sentencecase(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to Sentence case."""
    return await _local_endpoint(request, req, "sentencecase", ts.to_sentence_case, user, db)


@router.post("/titlecase", response_model=TextResponse)
async def titlecase(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to Title Case."""
    return await _local_endpoint(request, req, "titlecase", ts.to_title_case, user, db)


@router.post("/upper-camel-case", response_model=TextResponse)
async def upper_camel_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to UpperCamelCase (PascalCase)."""
    return await _local_endpoint(request, req, "upper-camel-case", ts.to_upper_camel_case, user, db)


@router.post("/lower-camel-case", response_model=TextResponse)
async def lower_camel_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to lowerCamelCase."""
    return await _local_endpoint(request, req, "lower-camel-case", ts.to_lower_camel_case, user, db)


@router.post("/snake-case", response_model=TextResponse)
async def snake_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to snake_case."""
    return await _local_endpoint(request, req, "snake-case", ts.to_snake_case, user, db)


@router.post("/kebab-case", response_model=TextResponse)
async def kebab_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to kebab-case."""
    return await _local_endpoint(request, req, "kebab-case", ts.to_kebab_case, user, db)


@router.post("/capitalize-words", response_model=TextResponse)
async def capitalize_words(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Capitalize the first letter of each word, keep rest unchanged."""
    return await _local_endpoint(request, req, "capitalize-words", ts.to_capitalize_words, user, db)


@router.post("/alternating-case", response_model=TextResponse)
async def alternating_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to aLtErNaTiNg CaSe."""
    return await _local_endpoint(request, req, "alternating-case", ts.to_alternating_case, user, db)


@router.post("/inverse-word-case", response_model=TextResponse)
async def inverse_word_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Capitalize last letter of each word instead of first."""
    return await _local_endpoint(request, req, "inverse-word-case", ts.to_inverse_word_case, user, db)


@router.post("/wide-text", response_model=TextResponse)
async def wide_text(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Add spaces between every character (aesthetic/vaporwave)."""
    return await _local_endpoint(request, req, "wide-text", ts.to_wide_text, user, db)


@router.post("/small-caps", response_model=TextResponse)
async def small_caps(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to Unicode small capital letters."""
    return await _local_endpoint(request, req, "small-caps", ts.to_small_caps, user, db)


@router.post("/upside-down", response_model=TextResponse)
async def upside_down(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Flip text upside down using Unicode characters."""
    return await _local_endpoint(request, req, "upside-down", ts.to_upside_down, user, db)


@router.post("/strikethrough", response_model=TextResponse)
async def strikethrough(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Apply Unicode strikethrough to each character."""
    return await _local_endpoint(request, req, "strikethrough", ts.to_strikethrough, user, db)


@router.post("/ap-title-case", response_model=TextResponse)
async def ap_title_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Smart title case following AP style rules."""
    return await _local_endpoint(request, req, "ap-title-case", ts.to_ap_title_case, user, db)


@router.post("/swap-word-case", response_model=TextResponse)
async def swap_word_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Alternate case at the word level (UPPER lower UPPER lower)."""
    return await _local_endpoint(request, req, "swap-word-case", ts.to_swap_word_case, user, db)


@router.post("/dot-case", response_model=TextResponse)
async def dot_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Join words with dots (e.g. my.config.value)."""
    return await _local_endpoint(request, req, "dot-case", ts.to_dot_case, user, db)


@router.post("/constant-case", response_model=TextResponse)
async def constant_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to CONSTANT_CASE (SCREAMING_SNAKE_CASE)."""
    return await _local_endpoint(request, req, "constant-case", ts.to_constant_case, user, db)


@router.post("/train-case", response_model=TextResponse)
async def train_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Capitalize each word and join with hyphens (Train-Case)."""
    return await _local_endpoint(request, req, "train-case", ts.to_train_case, user, db)


@router.post("/path-case", response_model=TextResponse)
async def path_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Join words with forward slashes (my/file/path)."""
    return await _local_endpoint(request, req, "path-case", ts.to_path_case, user, db)


@router.post("/flat-case", response_model=TextResponse)
async def flat_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """All lowercase with no separators (flatcase)."""
    return await _local_endpoint(request, req, "flat-case", ts.to_flat_case, user, db)


@router.post("/cobol-case", response_model=TextResponse)
async def cobol_case(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert text to COBOL-CASE (uppercase with hyphens)."""
    return await _local_endpoint(request, req, "cobol-case", ts.to_cobol_case, user, db)


@router.post("/remove-extra-spaces", response_model=TextResponse)
async def remove_extra_spaces(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Collapse multiple whitespace runs into a single space."""
    return await _local_endpoint(request, req, "remove-extra-spaces", ts.remove_extra_spaces, user, db)


@router.post("/remove-all-spaces", response_model=TextResponse)
async def remove_all_spaces(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Strip all whitespace from text."""
    return await _local_endpoint(request, req, "remove-all-spaces", ts.remove_all_spaces, user, db)


@router.post("/remove-line-breaks", response_model=TextResponse)
async def remove_line_breaks(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Replace line breaks with spaces."""
    return await _local_endpoint(request, req, "remove-line-breaks", ts.remove_line_breaks, user, db)


# ── Text Cleaning ────────────────────────────────────────────────────────

@router.post("/strip-html", response_model=TextResponse)
async def strip_html(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Remove HTML tags and decode entities."""
    return await _local_endpoint(request, req, "strip-html", ts.strip_html, user, db)


@router.post("/remove-accents", response_model=TextResponse)
async def remove_accents(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Remove diacritics/accents from text."""
    return await _local_endpoint(request, req, "remove-accents", ts.remove_accents, user, db)


@router.post("/toggle-smart-quotes", response_model=TextResponse)
async def toggle_smart_quotes(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Toggle between smart (curly) and straight quotes."""
    return await _local_endpoint(request, req, "toggle-smart-quotes", ts.toggle_smart_quotes, user, db)


# ── Encoding ──────────────────────────────────────────────────────────────────

@router.post("/base64-encode", response_model=TextResponse)
async def base64_encode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Encode text to Base64."""
    return await _local_endpoint(request, req, "base64-encode", ts.base64_encode, user, db)


@router.post("/base64-decode", response_model=TextResponse)
async def base64_decode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Decode Base64 text."""
    await _enforce_tool_access(request, "base64-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.base64_decode(req.text), operation="base64-decode")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Base64 input")


@router.post("/url-encode", response_model=TextResponse)
async def url_encode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Percent-encode text for use in a URL."""
    return await _local_endpoint(request, req, "url-encode", ts.url_encode, user, db)


@router.post("/url-decode", response_model=TextResponse)
async def url_decode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Decode a percent-encoded URL string."""
    await _enforce_tool_access(request, "url-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.url_decode(req.text), operation="url-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid URL-encoded input")


@router.post("/hex-encode", response_model=TextResponse)
async def hex_encode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Encode text to hexadecimal."""
    return await _local_endpoint(request, req, "hex-encode", ts.hex_encode, user, db)


@router.post("/hex-decode", response_model=TextResponse)
async def hex_decode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Decode hexadecimal to text."""
    await _enforce_tool_access(request, "hex-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.hex_decode(req.text), operation="hex-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid hexadecimal input")


@router.post("/morse-encode", response_model=TextResponse)
async def morse_encode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Encode text to Morse code."""
    return await _local_endpoint(request, req, "morse-encode", ts.morse_encode, user, db)


@router.post("/morse-decode", response_model=TextResponse)
async def morse_decode(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Decode Morse code to text."""
    await _enforce_tool_access(request, "morse-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.morse_decode(req.text), operation="morse-decode")
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Morse code input")


# ── Text Tools ────────────────────────────────────────────────────────────────

@router.post("/reverse", response_model=TextResponse)
async def reverse(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Reverse the entire text."""
    return await _local_endpoint(request, req, "reverse", ts.reverse_text, user, db)


@router.post("/sort-lines-asc", response_model=TextResponse)
async def sort_lines_asc(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Sort lines alphabetically A → Z (case-insensitive)."""
    return await _local_endpoint(request, req, "sort-lines-asc", ts.sort_lines_asc, user, db)


@router.post("/sort-lines-desc", response_model=TextResponse)
async def sort_lines_desc(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Sort lines alphabetically Z → A (case-insensitive)."""
    return await _local_endpoint(request, req, "sort-lines-desc", ts.sort_lines_desc, user, db)


@router.post("/remove-duplicate-lines", response_model=TextResponse)
async def remove_duplicate_lines(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Remove duplicate lines, preserving first occurrence."""
    return await _local_endpoint(request, req, "remove-duplicate-lines", ts.remove_duplicate_lines, user, db)


@router.post("/reverse-lines", response_model=TextResponse)
async def reverse_lines(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Reverse line order."""
    return await _local_endpoint(request, req, "reverse-lines", ts.reverse_lines, user, db)


@router.post("/number-lines", response_model=TextResponse)
async def number_lines(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Prefix each line with its line number."""
    return await _local_endpoint(request, req, "number-lines", ts.number_lines, user, db)


@router.post("/rot13", response_model=TextResponse)
async def rot13(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Apply ROT13 cipher to text."""
    return await _local_endpoint(request, req, "rot13", ts.rot13, user, db)


# ── Developer Tools ───────────────────────────────────────────────────────────

@router.post("/format-json", response_model=TextResponse)
async def format_json(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Pretty-print JSON with 2-space indentation."""
    await _enforce_tool_access(request, "format-json", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.format_json(req.text), operation="format-json")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON input")


@router.post("/json-to-yaml", response_model=TextResponse)
async def json_to_yaml(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert JSON to YAML."""
    await _enforce_tool_access(request, "json-to-yaml", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_to_yaml(req.text), operation="json-to-yaml")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON input")


# ── Escape / Unescape ────────────────────────────────────────────────────────

@router.post("/json-escape", response_model=TextResponse)
async def json_escape(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Escape special characters for JSON strings."""
    return await _local_endpoint(request, req, "json-escape", ts.json_escape, user, db)


@router.post("/json-unescape", response_model=TextResponse)
async def json_unescape(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Unescape JSON string escape sequences."""
    await _enforce_tool_access(request, "json-unescape", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_unescape(req.text), operation="json-unescape")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON escaped input")


@router.post("/html-escape", response_model=TextResponse)
async def html_escape(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Escape HTML special characters to entities."""
    return await _local_endpoint(request, req, "html-escape", ts.html_escape_text, user, db)


@router.post("/html-unescape", response_model=TextResponse)
async def html_unescape(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Decode HTML entities to characters."""
    return await _local_endpoint(request, req, "html-unescape", ts.html_unescape_text, user, db)


# ── CSV / JSON Conversion ────────────────────────────────────────────────────

@router.post("/csv-to-json", response_model=TextResponse)
async def csv_to_json(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert CSV text to JSON array."""
    await _enforce_tool_access(request, "csv-to-json", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.csv_to_json(req.text), operation="csv-to-json")
    except (csv.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid CSV input")


@router.post("/json-to-csv", response_model=TextResponse)
async def json_to_csv(request: Request, req: TextRequest, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Convert JSON array of objects to CSV."""
    await _enforce_tool_access(request, "json-to-csv", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_to_csv(req.text), operation="json-to-csv")
    except (json.JSONDecodeError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid JSON input (expected array of objects)")


# ── AI Tools ─────────────────────────────────────────────────────────────────

@router.post("/generate-hashtags", response_model=TextResponse)
async def generate_hashtags(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate relevant hashtags from the input text."""
    return await _ai_endpoint(request, req, "generate-hashtags", HashtagService.generate_hashtags, "Hashtag generation failed", user=user, db=db)


@router.post("/generate-seo-titles", response_model=TextResponse)
async def generate_seo_titles(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate SEO-optimized title suggestions from the input text."""
    return await _ai_endpoint(request, req, "generate-seo-titles", SEOTitleService.generate_seo_titles, "SEO title generation failed", user=user, db=db)


@router.post("/generate-meta-descriptions", response_model=TextResponse)
async def generate_meta_descriptions(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate SEO meta description suggestions from the input text."""
    return await _ai_endpoint(request, req, "generate-meta-descriptions", MetaDescriptionService.generate_meta_descriptions, "Meta description generation failed", user=user, db=db)


@router.post("/generate-blog-outline", response_model=TextResponse)
async def generate_blog_outline(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a structured blog post outline from the input text."""
    return await _ai_endpoint(request, req, "generate-blog-outline", BlogOutlineService.generate_blog_outline, "Blog outline generation failed", user=user, db=db)


@router.post("/shorten-for-tweet", response_model=TextResponse)
async def shorten_for_tweet(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Shorten text to fit within a tweet (280 characters)."""
    return await _ai_endpoint(request, req, "shorten-for-tweet", TweetShortenerService.shorten_for_tweet, "Tweet shortening failed", user=user, db=db)


@router.post("/rewrite-email", response_model=TextResponse)
async def rewrite_email(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Rewrite text as a professional email."""
    return await _ai_endpoint(request, req, "rewrite-email", EmailRewriterService.rewrite_email, "Email rewriting failed", user=user, db=db)


@router.post("/extract-keywords", response_model=TextResponse)
async def extract_keywords(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Extract keywords from text."""
    return await _ai_endpoint(request, req, "extract-keywords", KeywordExtractorService.extract_keywords, "Keyword extraction failed", user=user, db=db)


@router.post("/translate", response_model=TextResponse)
async def translate(request: Request, req: TranslateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Translate text to the specified target language."""
    return await _ai_endpoint(request, req, f"translate-{req.target_language.lower()}", TranslatorService.translate, "Translation failed", req.target_language, user=user, db=db)


@router.post("/transliterate", response_model=TextResponse)
async def transliterate(request: Request, req: TranslateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Transliterate text into the script of the target language."""
    return await _ai_endpoint(request, req, f"transliterate-{req.target_language.lower()}", TransliterationService.transliterate, "Transliteration failed", req.target_language, user=user, db=db)


@router.post("/emojify", response_model=TextResponse)
async def emojify(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Add contextual emojis to text based on emotions, actions, and concepts."""
    return await _ai_endpoint(request, req, "emojify", EmojifyService.emojify, "Could not emojify text", user=user, db=db)


@router.post("/detect-language", response_model=TextResponse)
async def detect_language(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Detect the language of the input text."""
    return await _ai_endpoint(request, req, "detect-language", LanguageDetector.detect, "Could not detect language", user=user, db=db)


@router.post("/summarize", response_model=TextResponse)
async def summarize(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Summarize the input text."""
    return await _ai_endpoint(request, req, "summarize", SummarizerService.summarize, "Summarization failed", user=user, db=db)


@router.post("/fix-grammar", response_model=TextResponse)
async def fix_grammar(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fix grammar in the input text."""
    return await _ai_endpoint(request, req, "fix-grammar", GrammarFixerService.fix_grammar, "Grammar fixing failed", user=user, db=db)


@router.post("/paraphrase", response_model=TextResponse)
async def paraphrase(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Paraphrase the input text."""
    return await _ai_endpoint(request, req, "paraphrase", ParaphraserService.paraphrase, "Paraphrasing failed", user=user, db=db)


@router.post("/change-tone", response_model=TextResponse)
async def change_tone(request: Request, req: ToneRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Change the tone of the input text."""
    return await _ai_endpoint(request, req, f"tone-{req.tone.lower()}", ToneChangerService.change_tone, "Tone changing failed", req.tone, user=user, db=db)


@router.post("/analyze-sentiment", response_model=TextResponse)
async def analyze_sentiment(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Analyze the sentiment of the input text."""
    return await _ai_endpoint(request, req, "analyze-sentiment", SentimentAnalyzerService.analyze_sentiment, "Sentiment analysis failed", user=user, db=db)


@router.post("/lengthen-text", response_model=TextResponse)
async def lengthen_text(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Lengthen the input text with more detail."""
    return await _ai_endpoint(request, req, "lengthen-text", TextLengthenerService.lengthen, "Text lengthening failed", user=user, db=db)


@router.post("/eli5", response_model=TextResponse)
async def eli5(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Simplify text for easy understanding (ELI5)."""
    return await _ai_endpoint(request, req, "eli5", ELI5Service.eli5, "ELI5 simplification failed", user=user, db=db)


@router.post("/proofread", response_model=TextResponse)
async def proofread(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Proofread text with tracked-changes style suggestions."""
    return await _ai_endpoint(request, req, "proofread", ProofreadService.proofread, "Proofreading failed", user=user, db=db)


@router.post("/generate-title", response_model=TextResponse)
async def generate_title(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate concise titles/headlines for the input text."""
    return await _ai_endpoint(request, req, "generate-title", TitleGeneratorService.generate_title, "Title generation failed", user=user, db=db)


@router.post("/refactor-prompt", response_model=TextResponse)
async def refactor_prompt(request: Request, req: TextRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Refactor a prompt to use minimum tokens."""
    return await _ai_endpoint(request, req, "refactor-prompt", PromptRefactorService.refactor_prompt, "Prompt refactoring failed", user=user, db=db)


@router.post("/change-format", response_model=TextResponse)
async def change_format(request: Request, req: FormatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Change the format/structure of the input text."""
    return await _ai_endpoint(request, req, f"format-{req.format.lower()}", FormatChangerService.change_format, "Format changing failed", req.format, user=user, db=db)

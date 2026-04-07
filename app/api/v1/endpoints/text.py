"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

import binascii
import csv
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_optional_user
from app.core.rate_limit import ai_limiter
from app.db.models import User
from app.db.session import get_db
from app.schemas.text import (
    CaesarRequest,
    FilterRequest,
    FormatRequest,
    KeyedCipherRequest,
    NthLineRequest,
    PadRequest,
    RailFenceRequest,
    SplitJoinRequest,
    SubstitutionRequest,
    TextRequest,
    TextResponse,
    ToneRequest,
    TranslateRequest,
    TruncateRequest,
    WrapRequest,
)
from app.services import text_service as ts
from app.services.ai_service import (
    # New AI services
    AcademicStyleService,
    ActiveVoiceService,
    AdCopyService,
    AngleGeneratorService,
    AntonymFinderService,
    BlogOutlineService,
    ClicheDetectorService,
    ConcisenessService,
    ContentIdeasService,
    ContinueWritingService,
    CoverLetterService,
    CreativeStyleService,
    CtaGeneratorService,
    DefineWordsService,
    ELI5Service,
    EmailRewriterService,
    EmailSubjectService,
    EmojifyService,
    FaqSchemaService,
    FormalityDetectorService,
    FormatChangerService,
    GrammarExplainService,
    GrammarFixerService,
    HashtagService,
    HookGeneratorService,
    InstagramCaptionService,
    JargonSimplifierService,
    KeywordExtractorService,
    LandingHeadlineService,
    LanguageDetector,
    LinkedinPostService,
    MeetingNotesService,
    MetaDescriptionService,
    MockApiResponseService,
    OutlineToDraftService,
    ParaphraserService,
    PosTaggerService,
    ProductDescService,
    PromptRefactorService,
    ProofreadService,
    RedundancyRemoverService,
    RegexGenService,
    ResumeBulletsService,
    RewriteUniqueService,
    SentenceSplitterService,
    SentenceTypeService,
    SentimentAnalyzerService,
    SEOTitleService,
    SocialBioService,
    SummarizerService,
    SynonymFinderService,
    TeamNameGenService,
    TechnicalStyleService,
    TextLengthenerService,
    TitleGeneratorService,
    ToneAnalyzerService,
    ToneChangerService,
    TranslatorService,
    TransliterationService,
    TweetShortenerService,
    TwitterThreadService,
    VocabComplexityService,
    WordPowerService,
    WritingPromptService,
    YoutubeDescService,
)
from app.services.pass_service import check_tool_access, check_visitor_access, record_tool_discovery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/text", tags=["Text"])


# ── Helper ────────────────────────────────────────────────────────────────────


async def _local_endpoint(
    request: Request,
    req: TextRequest,
    operation: str,
    transform_fn,
    user: User | None = None,
    db: AsyncSession | None = None,
) -> TextResponse:
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
        _safe = lambda s: str(s).replace("\n", " ").replace("\r", " ")
        logger.warning(
            "ACCESS DENIED tool=%s type=%s user=%s reason=%s",
            _safe(tool_id),
            _safe(tool_type),
            str(user.id) if user else "visitor",
            _safe(result.get("message", "limit reached")),
        )
        raise HTTPException(
            status_code=429,
            detail=result.get("message", "Daily limit reached. Get a pass for more access!"),
        )

    # Record tool discovery for authenticated users (fire-and-forget, ON CONFLICT DO NOTHING)
    if user:
        await record_tool_discovery(user.id, tool_id, db)


async def _ai_endpoint(
    request: Request,
    req,
    operation: str,
    service_fn,
    error_detail: str,
    *extra_args,
    user: User = None,
    db: AsyncSession = None,
) -> TextResponse:
    """Shared handler for all AI-powered endpoints."""
    _safe = lambda s: str(s).replace("\n", " ").replace("\r", " ")
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("AI     op=%s user=%s ip=%s chars=%d", _safe(operation), user_id, client_ip, len(req.text))
    ai_limiter.check(request)
    if db:
        await _enforce_tool_access(request, operation, "ai", user, db)
    try:
        result = await service_fn(req.text, *extra_args)
        logger.info("AI     op=%s -> OK (%d chars)", _safe(operation), len(result))
        return TextResponse(original=req.text, result=result, operation=operation)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("AI     op=%s -> FAILED: %s", _safe(operation), _safe(exc))
        raise HTTPException(status_code=500, detail=error_detail) from exc


# ── Text Transformations ─────────────────────────────────────────────────────


@router.post("/uppercase", response_model=TextResponse)
async def uppercase(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to UPPERCASE."""
    return await _local_endpoint(request, req, "uppercase", ts.to_uppercase, user, db)


@router.post("/lowercase", response_model=TextResponse)
async def lowercase(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to lowercase."""
    return await _local_endpoint(request, req, "lowercase", ts.to_lowercase, user, db)


@router.post("/inversecase", response_model=TextResponse)
async def inversecase(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Invert case of every character."""
    return await _local_endpoint(request, req, "inversecase", ts.to_inverse_case, user, db)


@router.post("/sentencecase", response_model=TextResponse)
async def sentencecase(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to Sentence case."""
    return await _local_endpoint(request, req, "sentencecase", ts.to_sentence_case, user, db)


@router.post("/titlecase", response_model=TextResponse)
async def titlecase(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to Title Case."""
    return await _local_endpoint(request, req, "titlecase", ts.to_title_case, user, db)


@router.post("/upper-camel-case", response_model=TextResponse)
async def upper_camel_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to UpperCamelCase (PascalCase)."""
    return await _local_endpoint(request, req, "upper-camel-case", ts.to_upper_camel_case, user, db)


@router.post("/lower-camel-case", response_model=TextResponse)
async def lower_camel_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to lowerCamelCase."""
    return await _local_endpoint(request, req, "lower-camel-case", ts.to_lower_camel_case, user, db)


@router.post("/snake-case", response_model=TextResponse)
async def snake_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to snake_case."""
    return await _local_endpoint(request, req, "snake-case", ts.to_snake_case, user, db)


@router.post("/kebab-case", response_model=TextResponse)
async def kebab_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to kebab-case."""
    return await _local_endpoint(request, req, "kebab-case", ts.to_kebab_case, user, db)


@router.post("/capitalize-words", response_model=TextResponse)
async def capitalize_words(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Capitalize the first letter of each word, keep rest unchanged."""
    return await _local_endpoint(request, req, "capitalize-words", ts.to_capitalize_words, user, db)


@router.post("/alternating-case", response_model=TextResponse)
async def alternating_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to aLtErNaTiNg CaSe."""
    return await _local_endpoint(request, req, "alternating-case", ts.to_alternating_case, user, db)


@router.post("/inverse-word-case", response_model=TextResponse)
async def inverse_word_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Capitalize last letter of each word instead of first."""
    return await _local_endpoint(request, req, "inverse-word-case", ts.to_inverse_word_case, user, db)


@router.post("/wide-text", response_model=TextResponse)
async def wide_text(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Add spaces between every character (aesthetic/vaporwave)."""
    return await _local_endpoint(request, req, "wide-text", ts.to_wide_text, user, db)


@router.post("/small-caps", response_model=TextResponse)
async def small_caps(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to Unicode small capital letters."""
    return await _local_endpoint(request, req, "small-caps", ts.to_small_caps, user, db)


@router.post("/upside-down", response_model=TextResponse)
async def upside_down(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Flip text upside down using Unicode characters."""
    return await _local_endpoint(request, req, "upside-down", ts.to_upside_down, user, db)


@router.post("/strikethrough", response_model=TextResponse)
async def strikethrough(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply Unicode strikethrough to each character."""
    return await _local_endpoint(request, req, "strikethrough", ts.to_strikethrough, user, db)


@router.post("/ap-title-case", response_model=TextResponse)
async def ap_title_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Smart title case following AP style rules."""
    return await _local_endpoint(request, req, "ap-title-case", ts.to_ap_title_case, user, db)


@router.post("/swap-word-case", response_model=TextResponse)
async def swap_word_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Alternate case at the word level (UPPER lower UPPER lower)."""
    return await _local_endpoint(request, req, "swap-word-case", ts.to_swap_word_case, user, db)


@router.post("/dot-case", response_model=TextResponse)
async def dot_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Join words with dots (e.g. my.config.value)."""
    return await _local_endpoint(request, req, "dot-case", ts.to_dot_case, user, db)


@router.post("/constant-case", response_model=TextResponse)
async def constant_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to CONSTANT_CASE (SCREAMING_SNAKE_CASE)."""
    return await _local_endpoint(request, req, "constant-case", ts.to_constant_case, user, db)


@router.post("/train-case", response_model=TextResponse)
async def train_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Capitalize each word and join with hyphens (Train-Case)."""
    return await _local_endpoint(request, req, "train-case", ts.to_train_case, user, db)


@router.post("/path-case", response_model=TextResponse)
async def path_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Join words with forward slashes (my/file/path)."""
    return await _local_endpoint(request, req, "path-case", ts.to_path_case, user, db)


@router.post("/flat-case", response_model=TextResponse)
async def flat_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """All lowercase with no separators (flatcase)."""
    return await _local_endpoint(request, req, "flat-case", ts.to_flat_case, user, db)


@router.post("/cobol-case", response_model=TextResponse)
async def cobol_case(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to COBOL-CASE (uppercase with hyphens)."""
    return await _local_endpoint(request, req, "cobol-case", ts.to_cobol_case, user, db)


@router.post("/remove-extra-spaces", response_model=TextResponse)
async def remove_extra_spaces(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Collapse multiple whitespace runs into a single space."""
    return await _local_endpoint(request, req, "remove-extra-spaces", ts.remove_extra_spaces, user, db)


@router.post("/remove-all-spaces", response_model=TextResponse)
async def remove_all_spaces(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Strip all whitespace from text."""
    return await _local_endpoint(request, req, "remove-all-spaces", ts.remove_all_spaces, user, db)


@router.post("/remove-line-breaks", response_model=TextResponse)
async def remove_line_breaks(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Replace line breaks with spaces."""
    return await _local_endpoint(request, req, "remove-line-breaks", ts.remove_line_breaks, user, db)


# ── Text Cleaning ────────────────────────────────────────────────────────


@router.post("/strip-html", response_model=TextResponse)
async def strip_html(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove HTML tags and decode entities."""
    return await _local_endpoint(request, req, "strip-html", ts.strip_html, user, db)


@router.post("/remove-accents", response_model=TextResponse)
async def remove_accents(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove diacritics/accents from text."""
    return await _local_endpoint(request, req, "remove-accents", ts.remove_accents, user, db)


@router.post("/toggle-smart-quotes", response_model=TextResponse)
async def toggle_smart_quotes(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle between smart (curly) and straight quotes."""
    return await _local_endpoint(request, req, "toggle-smart-quotes", ts.toggle_smart_quotes, user, db)


@router.post("/strip-invisible", response_model=TextResponse)
async def strip_invisible(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove zero-width spaces, soft hyphens, and hidden Unicode characters."""
    return await _local_endpoint(request, req, "strip-invisible", ts.strip_invisible, user, db)


@router.post("/strip-emoji", response_model=TextResponse)
async def strip_emoji(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all emoji characters from text."""
    return await _local_endpoint(request, req, "strip-emoji", ts.strip_emoji, user, db)


@router.post("/normalize-whitespace", response_model=TextResponse)
async def normalize_whitespace(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert tabs, non-breaking spaces, and exotic whitespace to regular spaces."""
    return await _local_endpoint(request, req, "normalize-whitespace", ts.normalize_whitespace, user, db)


@router.post("/strip-non-ascii", response_model=TextResponse)
async def strip_non_ascii(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all non-ASCII characters."""
    return await _local_endpoint(request, req, "strip-non-ascii", ts.strip_non_ascii, user, db)


@router.post("/fix-line-endings", response_model=TextResponse)
async def fix_line_endings(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Normalize mixed line endings (CRLF/CR) to Unix-style LF."""
    return await _local_endpoint(request, req, "fix-line-endings", ts.fix_line_endings, user, db)


@router.post("/strip-markdown", response_model=TextResponse)
async def strip_markdown(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove Markdown formatting to get plain text."""
    return await _local_endpoint(request, req, "strip-markdown", ts.strip_markdown, user, db)


@router.post("/trim-lines", response_model=TextResponse)
async def trim_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove leading and trailing spaces from every line."""
    return await _local_endpoint(request, req, "trim-lines", ts.trim_lines, user, db)


@router.post("/strip-empty-lines", response_model=TextResponse)
async def strip_empty_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all blank lines, keeping only lines with content."""
    return await _local_endpoint(request, req, "strip-empty-lines", ts.strip_empty_lines, user, db)


@router.post("/strip-urls", response_model=TextResponse)
async def strip_urls(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Strip all URLs and web links from text."""
    return await _local_endpoint(request, req, "strip-urls", ts.strip_urls, user, db)


@router.post("/strip-emails", response_model=TextResponse)
async def strip_emails(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Strip all email addresses from text."""
    return await _local_endpoint(request, req, "strip-emails", ts.strip_emails, user, db)


@router.post("/normalize-punctuation", response_model=TextResponse)
async def normalize_punctuation(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Fix spaces around punctuation marks."""
    return await _local_endpoint(request, req, "normalize-punctuation", ts.normalize_punctuation, user, db)


@router.post("/strip-numbers", response_model=TextResponse)
async def strip_numbers(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all numeric digits from text."""
    return await _local_endpoint(request, req, "strip-numbers", ts.strip_numbers, user, db)


# ── Encoding ──────────────────────────────────────────────────────────────────


@router.post("/base64-encode", response_model=TextResponse)
async def base64_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to Base64."""
    return await _local_endpoint(request, req, "base64-encode", ts.base64_encode, user, db)


@router.post("/base64-decode", response_model=TextResponse)
async def base64_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode Base64 text."""
    await _enforce_tool_access(request, "base64-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.base64_decode(req.text), operation="base64-decode")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Base64 input") from None


@router.post("/url-encode", response_model=TextResponse)
async def url_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Percent-encode text for use in a URL."""
    return await _local_endpoint(request, req, "url-encode", ts.url_encode, user, db)


@router.post("/url-decode", response_model=TextResponse)
async def url_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode a percent-encoded URL string."""
    await _enforce_tool_access(request, "url-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.url_decode(req.text), operation="url-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid URL-encoded input") from None


@router.post("/hex-encode", response_model=TextResponse)
async def hex_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to hexadecimal."""
    return await _local_endpoint(request, req, "hex-encode", ts.hex_encode, user, db)


@router.post("/hex-decode", response_model=TextResponse)
async def hex_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode hexadecimal to text."""
    await _enforce_tool_access(request, "hex-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.hex_decode(req.text), operation="hex-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid hexadecimal input") from None


@router.post("/morse-encode", response_model=TextResponse)
async def morse_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to Morse code."""
    return await _local_endpoint(request, req, "morse-encode", ts.morse_encode, user, db)


@router.post("/morse-decode", response_model=TextResponse)
async def morse_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode Morse code to text."""
    await _enforce_tool_access(request, "morse-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.morse_decode(req.text), operation="morse-decode")
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Morse code input") from None


# ── Binary / Octal / Decimal Encoding ─────────────────────────────────────────


@router.post("/binary-encode", response_model=TextResponse)
async def binary_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to binary representation."""
    return await _local_endpoint(request, req, "binary-encode", ts.binary_encode, user, db)


@router.post("/binary-decode", response_model=TextResponse)
async def binary_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode binary representation back to text."""
    await _enforce_tool_access(request, "binary-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.binary_decode(req.text), operation="binary-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid binary input") from None


@router.post("/octal-encode", response_model=TextResponse)
async def octal_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to octal representation."""
    return await _local_endpoint(request, req, "octal-encode", ts.octal_encode, user, db)


@router.post("/octal-decode", response_model=TextResponse)
async def octal_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode octal representation back to text."""
    await _enforce_tool_access(request, "octal-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.octal_decode(req.text), operation="octal-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid octal input") from None


@router.post("/decimal-encode", response_model=TextResponse)
async def decimal_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to decimal character codes."""
    return await _local_endpoint(request, req, "decimal-encode", ts.decimal_encode, user, db)


@router.post("/decimal-decode", response_model=TextResponse)
async def decimal_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode decimal character codes back to text."""
    await _enforce_tool_access(request, "decimal-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.decimal_decode(req.text), operation="decimal-decode")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid decimal input") from None


# ── Unicode Escape / Unescape ─────────────────────────────────────────────────


@router.post("/unicode-escape", response_model=TextResponse)
async def unicode_escape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert characters to \\uXXXX escape sequences."""
    return await _local_endpoint(request, req, "unicode-escape", ts.unicode_escape, user, db)


@router.post("/unicode-unescape", response_model=TextResponse)
async def unicode_unescape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert \\uXXXX escape sequences back to characters."""
    await _enforce_tool_access(request, "unicode-unescape", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.unicode_unescape(req.text), operation="unicode-unescape")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid Unicode escape sequence") from None


# ── Brainfuck Encoding ─────────────────────────────────────────────────────────


@router.post("/brainfuck-encode", response_model=TextResponse)
async def brainfuck_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text as a Brainfuck program."""
    return await _local_endpoint(request, req, "brainfuck-encode", ts.brainfuck_encode, user, db)


@router.post("/brainfuck-decode", response_model=TextResponse)
async def brainfuck_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a Brainfuck program and return its output."""
    await _enforce_tool_access(request, "brainfuck-decode", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.brainfuck_decode(req.text), operation="brainfuck-decode")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Ciphers ───────────────────────────────────────────────────────────────────


@router.post("/atbash", response_model=TextResponse)
async def atbash(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply Atbash cipher (reverse alphabet substitution)."""
    return await _local_endpoint(request, req, "atbash", ts.atbash_cipher, user, db)


@router.post("/caesar-cipher", response_model=TextResponse)
async def caesar_cipher(
    request: Request,
    req: CaesarRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply Caesar cipher with custom shift."""
    if db:
        await _enforce_tool_access(request, "caesar-cipher", "api", user, db)
    result = ts.caesar_cipher(req.text, req.shift)
    return TextResponse(original=req.text, result=result, operation="caesar-cipher")


@router.post("/caesar-brute-force", response_model=TextResponse)
async def caesar_brute_force(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Try all 25 Caesar shifts to find plaintext."""
    return await _local_endpoint(request, req, "caesar-brute-force", ts.caesar_brute_force, user, db)


@router.post("/vigenere-encrypt", response_model=TextResponse)
async def vigenere_encrypt(
    request: Request,
    req: KeyedCipherRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encrypt text using Vigenere cipher."""
    if db:
        await _enforce_tool_access(request, "vigenere-encrypt", "api", user, db)
    try:
        result = ts.vigenere_encrypt(req.text, req.key)
        return TextResponse(original=req.text, result=result, operation="vigenere-encrypt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/vigenere-decrypt", response_model=TextResponse)
async def vigenere_decrypt(
    request: Request,
    req: KeyedCipherRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decrypt text using Vigenere cipher."""
    if db:
        await _enforce_tool_access(request, "vigenere-decrypt", "api", user, db)
    try:
        result = ts.vigenere_decrypt(req.text, req.key)
        return TextResponse(original=req.text, result=result, operation="vigenere-decrypt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/rail-fence-encrypt", response_model=TextResponse)
async def rail_fence_encrypt(
    request: Request,
    req: RailFenceRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encrypt text using Rail Fence cipher."""
    if db:
        await _enforce_tool_access(request, "rail-fence-encrypt", "api", user, db)
    result = ts.rail_fence_encrypt(req.text, req.rails)
    return TextResponse(original=req.text, result=result, operation="rail-fence-encrypt")


@router.post("/rail-fence-decrypt", response_model=TextResponse)
async def rail_fence_decrypt(
    request: Request,
    req: RailFenceRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decrypt text using Rail Fence cipher."""
    if db:
        await _enforce_tool_access(request, "rail-fence-decrypt", "api", user, db)
    result = ts.rail_fence_decrypt(req.text, req.rails)
    return TextResponse(original=req.text, result=result, operation="rail-fence-decrypt")


@router.post("/playfair-encrypt", response_model=TextResponse)
async def playfair_encrypt(
    request: Request,
    req: KeyedCipherRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encrypt text using Playfair cipher."""
    if db:
        await _enforce_tool_access(request, "playfair-encrypt", "api", user, db)
    try:
        result = ts.playfair_encrypt(req.text, req.key)
        return TextResponse(original=req.text, result=result, operation="playfair-encrypt")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/substitution-cipher", response_model=TextResponse)
async def substitution_cipher_route(
    request: Request,
    req: SubstitutionRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply custom substitution cipher."""
    if db:
        await _enforce_tool_access(request, "substitution-cipher", "api", user, db)
    try:
        result = ts.substitution_cipher(req.text, req.mapping)
        return TextResponse(original=req.text, result=result, operation="substitution-cipher")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/columnar-transposition", response_model=TextResponse)
async def columnar_transposition(
    request: Request,
    req: KeyedCipherRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply columnar transposition cipher."""
    if db:
        await _enforce_tool_access(request, "columnar-transposition", "api", user, db)
    try:
        result = ts.columnar_transposition(req.text, req.key)
        return TextResponse(original=req.text, result=result, operation="columnar-transposition")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/nato-phonetic", response_model=TextResponse)
async def nato_phonetic(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to/from NATO phonetic alphabet."""
    return await _local_endpoint(request, req, "nato-phonetic", ts.nato_phonetic, user, db)


@router.post("/bacon-cipher", response_model=TextResponse)
async def bacon_cipher(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode/decode using Bacon's biliteral cipher."""
    return await _local_endpoint(request, req, "bacon-cipher", ts.bacon_cipher, user, db)


# ── Encoding Extensions ─────────────────────────────────────────────────────


@router.post("/base32-encode", response_model=TextResponse)
async def base32_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to Base32."""
    return await _local_endpoint(request, req, "base32-encode", ts.base32_encode, user, db)


@router.post("/base32-decode", response_model=TextResponse)
async def base32_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode Base32 text."""
    try:
        return await _local_endpoint(request, req, "base32-decode", ts.base32_decode, user, db)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base32 input") from None


@router.post("/ascii85-encode", response_model=TextResponse)
async def ascii85_encode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Encode text to Ascii85."""
    return await _local_endpoint(request, req, "ascii85-encode", ts.ascii85_encode, user, db)


@router.post("/ascii85-decode", response_model=TextResponse)
async def ascii85_decode(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode Ascii85 text."""
    try:
        return await _local_endpoint(request, req, "ascii85-decode", ts.ascii85_decode, user, db)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Ascii85 input") from None


# ── Developer Tools (new) ───────────────────────────────────────────────────


@router.post("/xml-to-json", response_model=TextResponse)
async def xml_to_json(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert XML to JSON."""
    await _enforce_tool_access(request, "xml-to-json", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.xml_to_json(req.text), operation="xml-to-json")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid XML input") from None


@router.post("/csv-to-table", response_model=TextResponse)
async def csv_to_table(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert CSV to Markdown table."""
    return await _local_endpoint(request, req, "csv-to-table", ts.csv_to_table, user, db)


@router.post("/sql-insert-gen", response_model=TextResponse)
async def sql_insert_gen(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate SQL INSERT statements from CSV."""
    await _enforce_tool_access(request, "sql-insert-gen", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.sql_insert_gen(req.text), operation="sql-insert-gen")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Text Tools ────────────────────────────────────────────────────────────────


@router.post("/reverse", response_model=TextResponse)
async def reverse(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Reverse the entire text."""
    return await _local_endpoint(request, req, "reverse", ts.reverse_text, user, db)


@router.post("/sort-lines-asc", response_model=TextResponse)
async def sort_lines_asc(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Sort lines alphabetically A → Z (case-insensitive)."""
    return await _local_endpoint(request, req, "sort-lines-asc", ts.sort_lines_asc, user, db)


@router.post("/sort-lines-desc", response_model=TextResponse)
async def sort_lines_desc(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Sort lines alphabetically Z → A (case-insensitive)."""
    return await _local_endpoint(request, req, "sort-lines-desc", ts.sort_lines_desc, user, db)


@router.post("/remove-duplicate-lines", response_model=TextResponse)
async def remove_duplicate_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove duplicate lines, preserving first occurrence."""
    return await _local_endpoint(request, req, "remove-duplicate-lines", ts.remove_duplicate_lines, user, db)


@router.post("/reverse-lines", response_model=TextResponse)
async def reverse_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Reverse line order."""
    return await _local_endpoint(request, req, "reverse-lines", ts.reverse_lines, user, db)


@router.post("/number-lines", response_model=TextResponse)
async def number_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Prefix each line with its line number."""
    return await _local_endpoint(request, req, "number-lines", ts.number_lines, user, db)


@router.post("/shuffle-lines", response_model=TextResponse)
async def shuffle_lines(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Randomly shuffle the order of all lines."""
    return await _local_endpoint(request, req, "shuffle-lines", ts.shuffle_lines, user, db)


@router.post("/sort-by-length", response_model=TextResponse)
async def sort_by_length(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Sort lines from shortest to longest."""
    return await _local_endpoint(request, req, "sort-by-length", ts.sort_by_length, user, db)


@router.post("/sort-numeric", response_model=TextResponse)
async def sort_numeric(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Sort lines by their leading number in natural numeric order."""
    return await _local_endpoint(request, req, "sort-numeric", ts.sort_numeric, user, db)


@router.post("/line-frequency", response_model=TextResponse)
async def line_frequency(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Count how many times each unique line appears, sorted by frequency."""
    return await _local_endpoint(request, req, "line-frequency", ts.line_frequency, user, db)


@router.post("/split-to-lines", response_model=TextResponse)
async def split_to_lines(
    request: Request,
    req: SplitJoinRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Split text into separate lines by a delimiter."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=split-to-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "split-to-lines", "api", user, db)
    result = ts.split_to_lines(req.text, req.delimiter)
    return TextResponse(original=req.text, result=result, operation="split-to-lines")


@router.post("/join-lines", response_model=TextResponse)
async def join_lines(
    request: Request,
    req: SplitJoinRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge all lines into one using a chosen separator."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=join-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "join-lines", "api", user, db)
    result = ts.join_lines(req.text, req.delimiter)
    return TextResponse(original=req.text, result=result, operation="join-lines")


@router.post("/pad-lines", response_model=TextResponse)
async def pad_lines(
    request: Request,
    req: PadRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Pad all lines to equal width with spaces."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=pad-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "pad-lines", "api", user, db)
    result = ts.pad_lines(req.text, req.align)
    return TextResponse(original=req.text, result=result, operation="pad-lines")


@router.post("/wrap-lines", response_model=TextResponse)
async def wrap_lines(
    request: Request,
    req: WrapRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom prefix and/or suffix to every line."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=wrap-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "wrap-lines", "api", user, db)
    result = ts.wrap_lines(req.text, req.prefix, req.suffix)
    return TextResponse(original=req.text, result=result, operation="wrap-lines")


@router.post("/filter-lines", response_model=TextResponse)
async def filter_lines(
    request: Request,
    req: FilterRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Keep only lines that contain a specific word or phrase."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=filter-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "filter-lines", "api", user, db)
    result = ts.filter_lines_contain(req.text, req.pattern, req.case_sensitive, req.use_regex)
    return TextResponse(original=req.text, result=result, operation="filter-lines")


@router.post("/remove-lines", response_model=TextResponse)
async def remove_lines(
    request: Request,
    req: FilterRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all lines that contain a specific word or phrase."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=remove-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "remove-lines", "api", user, db)
    result = ts.remove_lines_contain(req.text, req.pattern, req.case_sensitive, req.use_regex)
    return TextResponse(original=req.text, result=result, operation="remove-lines")


@router.post("/truncate-lines", response_model=TextResponse)
async def truncate_lines(
    request: Request,
    req: TruncateRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Cut each line to a maximum character length."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=truncate-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "truncate-lines", "api", user, db)
    result = ts.truncate_lines(req.text, req.max_length)
    return TextResponse(original=req.text, result=result, operation="truncate-lines")


@router.post("/extract-nth-lines", response_model=TextResponse)
async def extract_nth_lines(
    request: Request,
    req: NthLineRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract every Nth line."""
    client_ip = request.client.host if request.client else "unknown"
    user_id = str(user.id) if user else "visitor"
    logger.info("LOCAL  op=extract-nth-lines user=%s ip=%s chars=%d", user_id, client_ip, len(req.text))
    if db:
        await _enforce_tool_access(request, "extract-nth-lines", "api", user, db)
    result = ts.extract_nth_lines(req.text, req.n, req.offset)
    return TextResponse(original=req.text, result=result, operation="extract-nth-lines")


@router.post("/rot13", response_model=TextResponse)
async def rot13(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply ROT13 cipher to text."""
    return await _local_endpoint(request, req, "rot13", ts.rot13, user, db)


# ── Developer Tools ───────────────────────────────────────────────────────────


@router.post("/format-json", response_model=TextResponse)
async def format_json(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Pretty-print JSON with 2-space indentation."""
    await _enforce_tool_access(request, "format-json", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.format_json(req.text), operation="format-json")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON input") from None


@router.post("/json-to-yaml", response_model=TextResponse)
async def json_to_yaml(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert JSON to YAML."""
    await _enforce_tool_access(request, "json-to-yaml", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_to_yaml(req.text), operation="json-to-yaml")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON input") from None


# ── Escape / Unescape ────────────────────────────────────────────────────────


@router.post("/json-escape", response_model=TextResponse)
async def json_escape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Escape special characters for JSON strings."""
    return await _local_endpoint(request, req, "json-escape", ts.json_escape, user, db)


@router.post("/json-unescape", response_model=TextResponse)
async def json_unescape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Unescape JSON string escape sequences."""
    await _enforce_tool_access(request, "json-unescape", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_unescape(req.text), operation="json-unescape")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON escaped input") from None


@router.post("/html-escape", response_model=TextResponse)
async def html_escape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Escape HTML special characters to entities."""
    return await _local_endpoint(request, req, "html-escape", ts.html_escape_text, user, db)


@router.post("/html-unescape", response_model=TextResponse)
async def html_unescape(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Decode HTML entities to characters."""
    return await _local_endpoint(request, req, "html-unescape", ts.html_unescape_text, user, db)


# ── CSV / JSON Conversion ────────────────────────────────────────────────────


@router.post("/csv-to-json", response_model=TextResponse)
async def csv_to_json(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert CSV text to JSON array."""
    await _enforce_tool_access(request, "csv-to-json", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.csv_to_json(req.text), operation="csv-to-json")
    except (csv.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid CSV input") from None


@router.post("/json-to-csv", response_model=TextResponse)
async def json_to_csv(
    request: Request,
    req: TextRequest,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert JSON array of objects to CSV."""
    await _enforce_tool_access(request, "json-to-csv", "api", user, db)
    try:
        return TextResponse(original=req.text, result=ts.json_to_csv(req.text), operation="json-to-csv")
    except (json.JSONDecodeError, ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid JSON input (expected array of objects)") from None


# ── AI Tools ─────────────────────────────────────────────────────────────────


@router.post("/generate-hashtags", response_model=TextResponse)
async def generate_hashtags(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate relevant hashtags from the input text."""
    return await _ai_endpoint(
        request,
        req,
        "generate-hashtags",
        HashtagService.generate_hashtags,
        "Hashtag generation failed",
        user=user,
        db=db,
    )


@router.post("/generate-seo-titles", response_model=TextResponse)
async def generate_seo_titles(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate SEO-optimized title suggestions from the input text."""
    return await _ai_endpoint(
        request,
        req,
        "generate-seo-titles",
        SEOTitleService.generate_seo_titles,
        "SEO title generation failed",
        user=user,
        db=db,
    )


@router.post("/generate-meta-descriptions", response_model=TextResponse)
async def generate_meta_descriptions(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate SEO meta description suggestions from the input text."""
    return await _ai_endpoint(
        request,
        req,
        "generate-meta-descriptions",
        MetaDescriptionService.generate_meta_descriptions,
        "Meta description generation failed",
        user=user,
        db=db,
    )


@router.post("/generate-blog-outline", response_model=TextResponse)
async def generate_blog_outline(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured blog post outline from the input text."""
    return await _ai_endpoint(
        request,
        req,
        "generate-blog-outline",
        BlogOutlineService.generate_blog_outline,
        "Blog outline generation failed",
        user=user,
        db=db,
    )


@router.post("/shorten-for-tweet", response_model=TextResponse)
async def shorten_for_tweet(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Shorten text to fit within a tweet (280 characters)."""
    return await _ai_endpoint(
        request,
        req,
        "shorten-for-tweet",
        TweetShortenerService.shorten_for_tweet,
        "Tweet shortening failed",
        user=user,
        db=db,
    )


@router.post("/rewrite-email", response_model=TextResponse)
async def rewrite_email(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rewrite text as a professional email."""
    return await _ai_endpoint(
        request,
        req,
        "rewrite-email",
        EmailRewriterService.rewrite_email,
        "Email rewriting failed",
        user=user,
        db=db,
    )


@router.post("/extract-keywords", response_model=TextResponse)
async def extract_keywords(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract keywords from text."""
    return await _ai_endpoint(
        request,
        req,
        "extract-keywords",
        KeywordExtractorService.extract_keywords,
        "Keyword extraction failed",
        user=user,
        db=db,
    )


@router.post("/translate", response_model=TextResponse)
async def translate(
    request: Request,
    req: TranslateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Translate text to the specified target language."""
    return await _ai_endpoint(
        request,
        req,
        f"translate-{req.target_language.lower()}",
        TranslatorService.translate,
        "Translation failed",
        req.target_language,
        user=user,
        db=db,
    )


@router.post("/transliterate", response_model=TextResponse)
async def transliterate(
    request: Request,
    req: TranslateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transliterate text into the script of the target language."""
    return await _ai_endpoint(
        request,
        req,
        f"transliterate-{req.target_language.lower()}",
        TransliterationService.transliterate,
        "Transliteration failed",
        req.target_language,
        user=user,
        db=db,
    )


@router.post("/emojify", response_model=TextResponse)
async def emojify(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add contextual emojis to text based on emotions, actions, and concepts."""
    return await _ai_endpoint(
        request,
        req,
        "emojify",
        EmojifyService.emojify,
        "Could not emojify text",
        user=user,
        db=db,
    )


@router.post("/detect-language", response_model=TextResponse)
async def detect_language(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect the language of the input text."""
    return await _ai_endpoint(
        request,
        req,
        "detect-language",
        LanguageDetector.detect,
        "Could not detect language",
        user=user,
        db=db,
    )


@router.post("/summarize", response_model=TextResponse)
async def summarize(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summarize the input text."""
    return await _ai_endpoint(
        request,
        req,
        "summarize",
        SummarizerService.summarize,
        "Summarization failed",
        user=user,
        db=db,
    )


@router.post("/fix-grammar", response_model=TextResponse)
async def fix_grammar(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fix grammar in the input text."""
    return await _ai_endpoint(
        request,
        req,
        "fix-grammar",
        GrammarFixerService.fix_grammar,
        "Grammar fixing failed",
        user=user,
        db=db,
    )


@router.post("/paraphrase", response_model=TextResponse)
async def paraphrase(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paraphrase the input text."""
    return await _ai_endpoint(
        request,
        req,
        "paraphrase",
        ParaphraserService.paraphrase,
        "Paraphrasing failed",
        user=user,
        db=db,
    )


@router.post("/change-tone", response_model=TextResponse)
async def change_tone(
    request: Request,
    req: ToneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the tone of the input text."""
    return await _ai_endpoint(
        request,
        req,
        f"tone-{req.tone.lower()}",
        ToneChangerService.change_tone,
        "Tone changing failed",
        req.tone,
        user=user,
        db=db,
    )


@router.post("/analyze-sentiment", response_model=TextResponse)
async def analyze_sentiment(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze the sentiment of the input text."""
    return await _ai_endpoint(
        request,
        req,
        "analyze-sentiment",
        SentimentAnalyzerService.analyze_sentiment,
        "Sentiment analysis failed",
        user=user,
        db=db,
    )


@router.post("/lengthen-text", response_model=TextResponse)
async def lengthen_text(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lengthen the input text with more detail."""
    return await _ai_endpoint(
        request,
        req,
        "lengthen-text",
        TextLengthenerService.lengthen,
        "Text lengthening failed",
        user=user,
        db=db,
    )


@router.post("/eli5", response_model=TextResponse)
async def eli5(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simplify text for easy understanding (ELI5)."""
    return await _ai_endpoint(request, req, "eli5", ELI5Service.eli5, "ELI5 simplification failed", user=user, db=db)


@router.post("/proofread", response_model=TextResponse)
async def proofread(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Proofread text with tracked-changes style suggestions."""
    return await _ai_endpoint(
        request,
        req,
        "proofread",
        ProofreadService.proofread,
        "Proofreading failed",
        user=user,
        db=db,
    )


@router.post("/generate-title", response_model=TextResponse)
async def generate_title(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate concise titles/headlines for the input text."""
    return await _ai_endpoint(
        request,
        req,
        "generate-title",
        TitleGeneratorService.generate_title,
        "Title generation failed",
        user=user,
        db=db,
    )


@router.post("/refactor-prompt", response_model=TextResponse)
async def refactor_prompt(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refactor a prompt to use minimum tokens."""
    return await _ai_endpoint(
        request,
        req,
        "refactor-prompt",
        PromptRefactorService.refactor_prompt,
        "Prompt refactoring failed",
        user=user,
        db=db,
    )


@router.post("/change-format", response_model=TextResponse)
async def change_format(
    request: Request,
    req: FormatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the format/structure of the input text."""
    return await _ai_endpoint(
        request,
        req,
        f"format-{req.format.lower()}",
        FormatChangerService.change_format,
        "Format changing failed",
        req.format,
        user=user,
        db=db,
    )


# ── New AI Writing Endpoints ─────────────────────────────────────────────────


@router.post("/academic-style", response_model=TextResponse)
async def academic_style(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "academic-style",
        AcademicStyleService.transform,
        "Academic style failed",
        user=user,
        db=db,
    )


@router.post("/creative-style", response_model=TextResponse)
async def creative_style(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "creative-style",
        CreativeStyleService.transform,
        "Creative style failed",
        user=user,
        db=db,
    )


@router.post("/technical-style", response_model=TextResponse)
async def technical_style(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "technical-style",
        TechnicalStyleService.transform,
        "Technical style failed",
        user=user,
        db=db,
    )


@router.post("/active-voice", response_model=TextResponse)
async def active_voice(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "active-voice",
        ActiveVoiceService.transform,
        "Active voice conversion failed",
        user=user,
        db=db,
    )


@router.post("/redundancy-remover", response_model=TextResponse)
async def redundancy_remover(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "redundancy-remover",
        RedundancyRemoverService.transform,
        "Redundancy removal failed",
        user=user,
        db=db,
    )


@router.post("/sentence-splitter", response_model=TextResponse)
async def sentence_splitter(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "sentence-splitter",
        SentenceSplitterService.transform,
        "Sentence splitting failed",
        user=user,
        db=db,
    )


@router.post("/conciseness", response_model=TextResponse)
async def conciseness(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "conciseness",
        ConcisenessService.transform,
        "Conciseness failed",
        user=user,
        db=db,
    )


@router.post("/resume-bullets", response_model=TextResponse)
async def resume_bullets(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "resume-bullets",
        ResumeBulletsService.transform,
        "Resume bullets failed",
        user=user,
        db=db,
    )


@router.post("/meeting-notes", response_model=TextResponse)
async def meeting_notes(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "meeting-notes",
        MeetingNotesService.transform,
        "Meeting notes failed",
        user=user,
        db=db,
    )


@router.post("/cover-letter", response_model=TextResponse)
async def cover_letter(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "cover-letter",
        CoverLetterService.transform,
        "Cover letter failed",
        user=user,
        db=db,
    )


@router.post("/outline-to-draft", response_model=TextResponse)
async def outline_to_draft(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "outline-to-draft",
        OutlineToDraftService.transform,
        "Outline expansion failed",
        user=user,
        db=db,
    )


@router.post("/continue-writing", response_model=TextResponse)
async def continue_writing(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "continue-writing",
        ContinueWritingService.transform,
        "Continue writing failed",
        user=user,
        db=db,
    )


@router.post("/rewrite-unique", response_model=TextResponse)
async def rewrite_unique(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "rewrite-unique",
        RewriteUniqueService.transform,
        "Unique rewriting failed",
        user=user,
        db=db,
    )


@router.post("/tone-analyzer", response_model=TextResponse)
async def tone_analyzer(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "tone-analyzer",
        ToneAnalyzerService.transform,
        "Tone analysis failed",
        user=user,
        db=db,
    )


# ── New AI Content Endpoints ─────────────────────────────────────────────────


@router.post("/linkedin-post", response_model=TextResponse)
async def linkedin_post(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "linkedin-post",
        LinkedinPostService.transform,
        "LinkedIn post failed",
        user=user,
        db=db,
    )


@router.post("/twitter-thread", response_model=TextResponse)
async def twitter_thread(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "twitter-thread",
        TwitterThreadService.transform,
        "Twitter thread failed",
        user=user,
        db=db,
    )


@router.post("/instagram-caption", response_model=TextResponse)
async def instagram_caption(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "instagram-caption",
        InstagramCaptionService.transform,
        "Instagram caption failed",
        user=user,
        db=db,
    )


@router.post("/youtube-description", response_model=TextResponse)
async def youtube_description(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "youtube-description",
        YoutubeDescService.transform,
        "YouTube description failed",
        user=user,
        db=db,
    )


@router.post("/social-bio", response_model=TextResponse)
async def social_bio(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "social-bio",
        SocialBioService.transform,
        "Social bio failed",
        user=user,
        db=db,
    )


@router.post("/product-description", response_model=TextResponse)
async def product_description(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "product-description",
        ProductDescService.transform,
        "Product description failed",
        user=user,
        db=db,
    )


@router.post("/cta-generator", response_model=TextResponse)
async def cta_generator(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "cta-generator",
        CtaGeneratorService.transform,
        "CTA generation failed",
        user=user,
        db=db,
    )


@router.post("/ad-copy", response_model=TextResponse)
async def ad_copy(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(request, req, "ad-copy", AdCopyService.transform, "Ad copy failed", user=user, db=db)


@router.post("/landing-headline", response_model=TextResponse)
async def landing_headline(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "landing-headline",
        LandingHeadlineService.transform,
        "Landing headline failed",
        user=user,
        db=db,
    )


@router.post("/email-subject", response_model=TextResponse)
async def email_subject(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "email-subject",
        EmailSubjectService.transform,
        "Email subject failed",
        user=user,
        db=db,
    )


@router.post("/content-ideas", response_model=TextResponse)
async def content_ideas(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "content-ideas",
        ContentIdeasService.transform,
        "Content ideas failed",
        user=user,
        db=db,
    )


@router.post("/hook-generator", response_model=TextResponse)
async def hook_generator(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "hook-generator",
        HookGeneratorService.transform,
        "Hook generation failed",
        user=user,
        db=db,
    )


@router.post("/angle-generator", response_model=TextResponse)
async def angle_generator(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "angle-generator",
        AngleGeneratorService.transform,
        "Angle generation failed",
        user=user,
        db=db,
    )


@router.post("/faq-schema", response_model=TextResponse)
async def faq_schema(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "faq-schema",
        FaqSchemaService.transform,
        "FAQ schema failed",
        user=user,
        db=db,
    )


# ── New Language Endpoints ───────────────────────────────────────────────────


@router.post("/pos-tagger", response_model=TextResponse)
async def pos_tagger(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "pos-tagger",
        PosTaggerService.transform,
        "POS tagging failed",
        user=user,
        db=db,
    )


@router.post("/sentence-type", response_model=TextResponse)
async def sentence_type(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "sentence-type",
        SentenceTypeService.transform,
        "Sentence classification failed",
        user=user,
        db=db,
    )


@router.post("/grammar-explain", response_model=TextResponse)
async def grammar_explain(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "grammar-explain",
        GrammarExplainService.transform,
        "Grammar explanation failed",
        user=user,
        db=db,
    )


@router.post("/synonym-finder", response_model=TextResponse)
async def synonym_finder(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "synonym-finder",
        SynonymFinderService.transform,
        "Synonym finding failed",
        user=user,
        db=db,
    )


@router.post("/antonym-finder", response_model=TextResponse)
async def antonym_finder(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "antonym-finder",
        AntonymFinderService.transform,
        "Antonym finding failed",
        user=user,
        db=db,
    )


@router.post("/define-words", response_model=TextResponse)
async def define_words(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "define-words",
        DefineWordsService.transform,
        "Word definition failed",
        user=user,
        db=db,
    )


@router.post("/word-power", response_model=TextResponse)
async def word_power(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "word-power",
        WordPowerService.transform,
        "Word power failed",
        user=user,
        db=db,
    )


@router.post("/vocab-complexity", response_model=TextResponse)
async def vocab_complexity(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "vocab-complexity",
        VocabComplexityService.transform,
        "Vocab complexity failed",
        user=user,
        db=db,
    )


@router.post("/jargon-simplifier", response_model=TextResponse)
async def jargon_simplifier(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "jargon-simplifier",
        JargonSimplifierService.transform,
        "Jargon simplification failed",
        user=user,
        db=db,
    )


@router.post("/formality-detector", response_model=TextResponse)
async def formality_detector(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "formality-detector",
        FormalityDetectorService.transform,
        "Formality detection failed",
        user=user,
        db=db,
    )


@router.post("/cliche-detector", response_model=TextResponse)
async def cliche_detector(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "cliche-detector",
        ClicheDetectorService.transform,
        "Cliche detection failed",
        user=user,
        db=db,
    )


# ── New Generator AI Endpoints ──────────────────────────────────────────────


@router.post("/regex-generator", response_model=TextResponse)
async def regex_generator(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "regex-generator",
        RegexGenService.transform,
        "Regex generation failed",
        user=user,
        db=db,
    )


@router.post("/writing-prompt", response_model=TextResponse)
async def writing_prompt(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "writing-prompt",
        WritingPromptService.transform,
        "Writing prompt failed",
        user=user,
        db=db,
    )


@router.post("/team-name-generator", response_model=TextResponse)
async def team_name_generator(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "team-name-generator",
        TeamNameGenService.transform,
        "Team name generation failed",
        user=user,
        db=db,
    )


@router.post("/mock-api-response", response_model=TextResponse)
async def mock_api_response(
    request: Request,
    req: TextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _ai_endpoint(
        request,
        req,
        "mock-api-response",
        MockApiResponseService.transform,
        "Mock API response failed",
        user=user,
        db=db,
    )

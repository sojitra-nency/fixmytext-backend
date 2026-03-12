"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.text import TextRequest, TextResponse, TranslateRequest, ToneRequest, FormatRequest
from app.core.rate_limit import ai_limiter
from app.core.deps import get_current_user
from app.db.models import User
from app.services.text_service import TextService
from app.services.ai_service import (
    HashtagService, SEOTitleService, MetaDescriptionService, BlogOutlineService,
    TweetShortenerService, EmailRewriterService,
    KeywordExtractorService, TranslatorService, TransliterationService,
    SummarizerService, GrammarFixerService,
    ParaphraserService, ToneChangerService, SentimentAnalyzerService,
    TextLengthenerService, FormatChangerService,
    ELI5Service, ProofreadService, TitleGeneratorService, PromptRefactorService,
)

router = APIRouter(prefix="/text", tags=["Text"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _transform(req: TextRequest, operation: str, fn) -> TextResponse:
    return TextResponse(
        original=req.text,
        result=fn(req.text),
        operation=operation,
    )


async def _ai_endpoint(request: Request, req, operation: str, service_fn, error_detail: str, *extra_args) -> TextResponse:
    """Shared handler for all AI-powered endpoints."""
    ai_limiter.check(request)
    try:
        result = await service_fn(req.text, *extra_args)
        return TextResponse(original=req.text, result=result, operation=operation)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail=error_detail)


# ── Text Transformations ─────────────────────────────────────────────────────

@router.post("/uppercase", response_model=TextResponse)
async def uppercase(req: TextRequest):
    """Convert text to UPPERCASE."""
    return _transform(req, "uppercase", TextService.to_uppercase)


@router.post("/lowercase", response_model=TextResponse)
async def lowercase(req: TextRequest):
    """Convert text to lowercase."""
    return _transform(req, "lowercase", TextService.to_lowercase)


@router.post("/inversecase", response_model=TextResponse)
async def inversecase(req: TextRequest):
    """Invert case of every character."""
    return _transform(req, "inversecase", TextService.to_inverse_case)


@router.post("/sentencecase", response_model=TextResponse)
async def sentencecase(req: TextRequest):
    """Convert text to Sentence case."""
    return _transform(req, "sentencecase", TextService.to_sentence_case)


@router.post("/titlecase", response_model=TextResponse)
async def titlecase(req: TextRequest):
    """Convert text to Title Case."""
    return _transform(req, "titlecase", TextService.to_title_case)


@router.post("/upper-camel-case", response_model=TextResponse)
async def upper_camel_case(req: TextRequest):
    """Convert text to UpperCamelCase (PascalCase)."""
    return _transform(req, "upper-camel-case", TextService.to_upper_camel_case)


@router.post("/lower-camel-case", response_model=TextResponse)
async def lower_camel_case(req: TextRequest):
    """Convert text to lowerCamelCase."""
    return _transform(req, "lower-camel-case", TextService.to_lower_camel_case)


@router.post("/snake-case", response_model=TextResponse)
async def snake_case(req: TextRequest):
    """Convert text to snake_case."""
    return _transform(req, "snake-case", TextService.to_snake_case)


@router.post("/kebab-case", response_model=TextResponse)
async def kebab_case(req: TextRequest):
    """Convert text to kebab-case."""
    return _transform(req, "kebab-case", TextService.to_kebab_case)


@router.post("/remove-extra-spaces", response_model=TextResponse)
async def remove_extra_spaces(req: TextRequest):
    """Collapse multiple whitespace runs into a single space."""
    return _transform(req, "remove-extra-spaces", TextService.remove_extra_spaces)


@router.post("/remove-all-spaces", response_model=TextResponse)
async def remove_all_spaces(req: TextRequest):
    """Strip all whitespace from text."""
    return _transform(req, "remove-all-spaces", TextService.remove_all_spaces)


@router.post("/remove-line-breaks", response_model=TextResponse)
async def remove_line_breaks(req: TextRequest):
    """Replace line breaks with spaces."""
    return _transform(req, "remove-line-breaks", TextService.remove_line_breaks)



# ── Text Cleaning ────────────────────────────────────────────────────────

@router.post("/strip-html", response_model=TextResponse)
async def strip_html(req: TextRequest):
    """Remove HTML tags and decode entities."""
    return _transform(req, "strip-html", TextService.strip_html)


@router.post("/remove-accents", response_model=TextResponse)
async def remove_accents(req: TextRequest):
    """Remove diacritics/accents from text."""
    return _transform(req, "remove-accents", TextService.remove_accents)


@router.post("/toggle-smart-quotes", response_model=TextResponse)
async def toggle_smart_quotes(req: TextRequest):
    """Toggle between smart (curly) and straight quotes."""
    return _transform(req, "toggle-smart-quotes", TextService.toggle_smart_quotes)


# ── Encoding ──────────────────────────────────────────────────────────────────

@router.post("/base64-encode", response_model=TextResponse)
async def base64_encode(req: TextRequest):
    """Encode text to Base64."""
    return _transform(req, "base64-encode", TextService.base64_encode)


@router.post("/base64-decode", response_model=TextResponse)
async def base64_decode(req: TextRequest):
    """Decode Base64 text."""
    try:
        return _transform(req, "base64-decode", TextService.base64_decode)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 input")


@router.post("/url-encode", response_model=TextResponse)
async def url_encode(req: TextRequest):
    """Percent-encode text for use in a URL."""
    return _transform(req, "url-encode", TextService.url_encode)


@router.post("/url-decode", response_model=TextResponse)
async def url_decode(req: TextRequest):
    """Decode a percent-encoded URL string."""
    try:
        return _transform(req, "url-decode", TextService.url_decode)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL-encoded input")


@router.post("/hex-encode", response_model=TextResponse)
async def hex_encode(req: TextRequest):
    """Encode text to hexadecimal."""
    return _transform(req, "hex-encode", TextService.hex_encode)


@router.post("/hex-decode", response_model=TextResponse)
async def hex_decode(req: TextRequest):
    """Decode hexadecimal to text."""
    try:
        return _transform(req, "hex-decode", TextService.hex_decode)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hexadecimal input")


@router.post("/morse-encode", response_model=TextResponse)
async def morse_encode(req: TextRequest):
    """Encode text to Morse code."""
    return _transform(req, "morse-encode", TextService.morse_encode)


@router.post("/morse-decode", response_model=TextResponse)
async def morse_decode(req: TextRequest):
    """Decode Morse code to text."""
    try:
        return _transform(req, "morse-decode", TextService.morse_decode)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Morse code input")


# ── Text Tools ────────────────────────────────────────────────────────────────

@router.post("/reverse", response_model=TextResponse)
async def reverse(req: TextRequest):
    """Reverse the entire text."""
    return _transform(req, "reverse", TextService.reverse_text)


@router.post("/sort-lines-asc", response_model=TextResponse)
async def sort_lines_asc(req: TextRequest):
    """Sort lines alphabetically A → Z (case-insensitive)."""
    return _transform(req, "sort-lines-asc", TextService.sort_lines_asc)


@router.post("/sort-lines-desc", response_model=TextResponse)
async def sort_lines_desc(req: TextRequest):
    """Sort lines alphabetically Z → A (case-insensitive)."""
    return _transform(req, "sort-lines-desc", TextService.sort_lines_desc)


@router.post("/remove-duplicate-lines", response_model=TextResponse)
async def remove_duplicate_lines(req: TextRequest):
    """Remove duplicate lines, preserving first occurrence."""
    return _transform(req, "remove-duplicate-lines", TextService.remove_duplicate_lines)


@router.post("/reverse-lines", response_model=TextResponse)
async def reverse_lines(req: TextRequest):
    """Reverse line order."""
    return _transform(req, "reverse-lines", TextService.reverse_lines)


@router.post("/number-lines", response_model=TextResponse)
async def number_lines(req: TextRequest):
    """Prefix each line with its line number."""
    return _transform(req, "number-lines", TextService.number_lines)


@router.post("/rot13", response_model=TextResponse)
async def rot13(req: TextRequest):
    """Apply ROT13 cipher to text."""
    return _transform(req, "rot13", TextService.rot13)


# ── Developer Tools ───────────────────────────────────────────────────────────

@router.post("/format-json", response_model=TextResponse)
async def format_json(req: TextRequest):
    """Pretty-print JSON with 2-space indentation."""
    try:
        return _transform(req, "format-json", TextService.format_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON input")


@router.post("/json-to-yaml", response_model=TextResponse)
async def json_to_yaml(req: TextRequest):
    """Convert JSON to YAML."""
    try:
        return _transform(req, "json-to-yaml", TextService.json_to_yaml)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON input")


# ── Escape / Unescape ────────────────────────────────────────────────────────

@router.post("/json-escape", response_model=TextResponse)
async def json_escape(req: TextRequest):
    """Escape special characters for JSON strings."""
    return _transform(req, "json-escape", TextService.json_escape)


@router.post("/json-unescape", response_model=TextResponse)
async def json_unescape(req: TextRequest):
    """Unescape JSON string escape sequences."""
    try:
        return _transform(req, "json-unescape", TextService.json_unescape)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON escaped input")


@router.post("/html-escape", response_model=TextResponse)
async def html_escape(req: TextRequest):
    """Escape HTML special characters to entities."""
    return _transform(req, "html-escape", TextService.html_escape)


@router.post("/html-unescape", response_model=TextResponse)
async def html_unescape(req: TextRequest):
    """Decode HTML entities to characters."""
    return _transform(req, "html-unescape", TextService.html_unescape)


# ── CSV / JSON Conversion ────────────────────────────────────────────────────

@router.post("/csv-to-json", response_model=TextResponse)
async def csv_to_json(req: TextRequest):
    """Convert CSV text to JSON array."""
    try:
        return _transform(req, "csv-to-json", TextService.csv_to_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV input")


@router.post("/json-to-csv", response_model=TextResponse)
async def json_to_csv(req: TextRequest):
    """Convert JSON array of objects to CSV."""
    try:
        return _transform(req, "json-to-csv", TextService.json_to_csv)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON input (expected array of objects)")


# ── AI Tools ─────────────────────────────────────────────────────────────────

@router.post("/generate-hashtags", response_model=TextResponse)
async def generate_hashtags(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Generate relevant hashtags from the input text."""
    return await _ai_endpoint(request, req, "generate-hashtags", HashtagService.generate_hashtags, "Hashtag generation failed")


@router.post("/generate-seo-titles", response_model=TextResponse)
async def generate_seo_titles(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Generate SEO-optimized title suggestions from the input text."""
    return await _ai_endpoint(request, req, "generate-seo-titles", SEOTitleService.generate_seo_titles, "SEO title generation failed")


@router.post("/generate-meta-descriptions", response_model=TextResponse)
async def generate_meta_descriptions(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Generate SEO meta description suggestions from the input text."""
    return await _ai_endpoint(request, req, "generate-meta-descriptions", MetaDescriptionService.generate_meta_descriptions, "Meta description generation failed")


@router.post("/generate-blog-outline", response_model=TextResponse)
async def generate_blog_outline(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Generate a structured blog post outline from the input text."""
    return await _ai_endpoint(request, req, "generate-blog-outline", BlogOutlineService.generate_blog_outline, "Blog outline generation failed")


@router.post("/shorten-for-tweet", response_model=TextResponse)
async def shorten_for_tweet(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Shorten text to fit within a tweet (280 characters)."""
    return await _ai_endpoint(request, req, "shorten-for-tweet", TweetShortenerService.shorten_for_tweet, "Tweet shortening failed")


@router.post("/rewrite-email", response_model=TextResponse)
async def rewrite_email(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Rewrite text as a professional email."""
    return await _ai_endpoint(request, req, "rewrite-email", EmailRewriterService.rewrite_email, "Email rewriting failed")



@router.post("/extract-keywords", response_model=TextResponse)
async def extract_keywords(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Extract keywords from text."""
    return await _ai_endpoint(request, req, "extract-keywords", KeywordExtractorService.extract_keywords, "Keyword extraction failed")


@router.post("/translate", response_model=TextResponse)
async def translate(request: Request, req: TranslateRequest, user: User = Depends(get_current_user)):
    """Translate text to the specified target language."""
    return await _ai_endpoint(request, req, f"translate-{req.target_language.lower()}", TranslatorService.translate, "Translation failed", req.target_language)


@router.post("/transliterate", response_model=TextResponse)
async def transliterate(request: Request, req: TranslateRequest, user: User = Depends(get_current_user)):
    """Transliterate text into the script of the target language."""
    return await _ai_endpoint(request, req, f"transliterate-{req.target_language.lower()}", TransliterationService.transliterate, "Transliteration failed", req.target_language)



@router.post("/summarize", response_model=TextResponse)
async def summarize(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Summarize the input text."""
    return await _ai_endpoint(request, req, "summarize", SummarizerService.summarize, "Summarization failed")


@router.post("/fix-grammar", response_model=TextResponse)
async def fix_grammar(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Fix grammar in the input text."""
    return await _ai_endpoint(request, req, "fix-grammar", GrammarFixerService.fix_grammar, "Grammar fixing failed")


@router.post("/paraphrase", response_model=TextResponse)
async def paraphrase(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Paraphrase the input text."""
    return await _ai_endpoint(request, req, "paraphrase", ParaphraserService.paraphrase, "Paraphrasing failed")


@router.post("/change-tone", response_model=TextResponse)
async def change_tone(request: Request, req: ToneRequest, user: User = Depends(get_current_user)):
    """Change the tone of the input text."""
    return await _ai_endpoint(request, req, f"tone-{req.tone.lower()}", ToneChangerService.change_tone, "Tone changing failed", req.tone)


@router.post("/analyze-sentiment", response_model=TextResponse)
async def analyze_sentiment(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Analyze the sentiment of the input text."""
    return await _ai_endpoint(request, req, "analyze-sentiment", SentimentAnalyzerService.analyze_sentiment, "Sentiment analysis failed")



@router.post("/lengthen-text", response_model=TextResponse)
async def lengthen_text(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Lengthen the input text with more detail."""
    return await _ai_endpoint(request, req, "lengthen-text", TextLengthenerService.lengthen, "Text lengthening failed")


@router.post("/eli5", response_model=TextResponse)
async def eli5(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Simplify text for easy understanding (ELI5)."""
    return await _ai_endpoint(request, req, "eli5", ELI5Service.eli5, "ELI5 simplification failed")


@router.post("/proofread", response_model=TextResponse)
async def proofread(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Proofread text with tracked-changes style suggestions."""
    return await _ai_endpoint(request, req, "proofread", ProofreadService.proofread, "Proofreading failed")


@router.post("/generate-title", response_model=TextResponse)
async def generate_title(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Generate concise titles/headlines for the input text."""
    return await _ai_endpoint(request, req, "generate-title", TitleGeneratorService.generate_title, "Title generation failed")


@router.post("/refactor-prompt", response_model=TextResponse)
async def refactor_prompt(request: Request, req: TextRequest, user: User = Depends(get_current_user)):
    """Refactor a prompt to use minimum tokens."""
    return await _ai_endpoint(request, req, "refactor-prompt", PromptRefactorService.refactor_prompt, "Prompt refactoring failed")


@router.post("/change-format", response_model=TextResponse)
async def change_format(request: Request, req: FormatRequest, user: User = Depends(get_current_user)):
    """Change the format/structure of the input text."""
    return await _ai_endpoint(request, req, f"format-{req.format.lower()}", FormatChangerService.change_format, "Format changing failed", req.format)

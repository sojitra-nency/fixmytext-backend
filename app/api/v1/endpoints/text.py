"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

from fastapi import APIRouter, HTTPException
from app.models.text import TextRequest, TextResponse
from app.services.text_service import TextService
from app.services.ai_service import HashtagService, SEOTitleService, MetaDescriptionService, BlogOutlineService, TweetShortenerService, EmailRewriterService

router = APIRouter(prefix="/text", tags=["Text"])

# ── Helper ────────────────────────────────────────────────────────────────────

def _transform(req: TextRequest, operation: str, fn) -> TextResponse:
    return TextResponse(
        original=req.text,
        result=fn(req.text),
        operation=operation,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

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


@router.post("/minify", response_model=TextResponse)
async def minify(req: TextRequest):
    """Collapse all whitespace into single spaces."""
    return _transform(req, "minify", TextService.minify)


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


# ── AI Tools ─────────────────────────────────────────────────────────────────

@router.post("/generate-hashtags", response_model=TextResponse)
async def generate_hashtags(req: TextRequest):
    """Generate relevant hashtags from the input text."""
    try:
        result = await HashtagService.generate_hashtags(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="generate-hashtags",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Hashtag generation failed")


@router.post("/generate-seo-titles", response_model=TextResponse)
async def generate_seo_titles(req: TextRequest):
    """Generate SEO-optimized title suggestions from the input text."""
    try:
        result = await SEOTitleService.generate_seo_titles(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="generate-seo-titles",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="SEO title generation failed")


@router.post("/generate-meta-descriptions", response_model=TextResponse)
async def generate_meta_descriptions(req: TextRequest):
    """Generate SEO meta description suggestions from the input text."""
    try:
        result = await MetaDescriptionService.generate_meta_descriptions(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="generate-meta-descriptions",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Meta description generation failed")


@router.post("/generate-blog-outline", response_model=TextResponse)
async def generate_blog_outline(req: TextRequest):
    """Generate a structured blog post outline from the input text."""
    try:
        result = await BlogOutlineService.generate_blog_outline(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="generate-blog-outline",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Blog outline generation failed")


@router.post("/shorten-for-tweet", response_model=TextResponse)
async def shorten_for_tweet(req: TextRequest):
    """Shorten text to fit within a tweet (280 characters)."""
    try:
        result = await TweetShortenerService.shorten_for_tweet(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="shorten-for-tweet",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Tweet shortening failed")


@router.post("/rewrite-email", response_model=TextResponse)
async def rewrite_email(req: TextRequest):
    """Rewrite text as a professional email."""
    try:
        result = await EmailRewriterService.rewrite_email(req.text)
        return TextResponse(
            original=req.text,
            result=result,
            operation="rewrite-email",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Email rewriting failed")

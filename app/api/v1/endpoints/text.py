"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

from fastapi import APIRouter, HTTPException
from app.models.text import TextRequest, TextResponse
from app.services.text_service import TextService

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

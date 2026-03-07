"""
Text endpoint router.

All routes live under: /api/v1/text/...
"""

from fastapi import APIRouter
from app.models.text import TextRequest, TextResponse, TextAnalysisResponse
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


@router.post("/analyze", response_model=TextAnalysisResponse)
async def analyze(req: TextRequest):
    """Return word count, sentence count, character count, and reading time."""
    return TextAnalysisResponse(**TextService.analyze(req.text))

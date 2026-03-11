"""Pydantic models (schemas) for text-processing requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    """Payload sent by the client for any text transformation."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
        examples=["Hello World"],
    )


class TranslateRequest(BaseModel):
    """Payload for translation requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be translated.",
    )
    target_language: str = Field(
        default="English",
        description="The language to translate into.",
    )


class ToneRequest(BaseModel):
    """Payload for tone change requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to change tone of.",
    )
    tone: Literal["formal", "casual", "friendly"] = Field(
        default="formal",
        description="Target tone: formal, casual, or friendly.",
    )


class FormatRequest(BaseModel):
    """Payload for format change requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to reformat.",
    )
    format: Literal["paragraph", "bullets", "paragraph-bullets", "numbered", "qna", "table", "tldr", "headings"] = Field(
        default="paragraph",
        description="Target format: paragraph, bullets, paragraph-bullets, numbered, qna, table, tldr, headings.",
    )


class TextResponse(BaseModel):
    """Transformed text returned by the API."""

    original: str = Field(..., description="The original input text.")
    result: str = Field(..., description="The transformed output text.")
    operation: str = Field(..., description="Name of the operation performed.")

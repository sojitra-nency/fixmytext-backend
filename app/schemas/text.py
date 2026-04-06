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
    format: Literal[
        "paragraph",
        "bullets",
        "paragraph-bullets",
        "numbered",
        "qna",
        "table",
        "tldr",
        "headings",
    ] = Field(
        default="paragraph",
        description="Target format: paragraph, bullets, paragraph-bullets, numbered, qna, table, tldr, headings.",
    )


class SplitJoinRequest(BaseModel):
    """Payload for split-to-lines and join-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    delimiter: str = Field(
        default=",",
        max_length=20,
        description="Delimiter or separator character(s).",
    )


class PadRequest(BaseModel):
    """Payload for pad-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    align: Literal["left", "right", "center"] = Field(
        default="left",
        description="Alignment direction: left, right, or center.",
    )


class WrapRequest(BaseModel):
    """Payload for wrap-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    prefix: str = Field(
        default="",
        max_length=100,
        description="Text to prepend to each line.",
    )
    suffix: str = Field(
        default="",
        max_length=100,
        description="Text to append to each line.",
    )


class FilterRequest(BaseModel):
    """Payload for filter-lines and remove-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    pattern: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Word or phrase (or regex pattern) to match against each line.",
    )
    case_sensitive: bool = Field(
        default=False,
        description="If true, match is case-sensitive.",
    )
    use_regex: bool = Field(
        default=False,
        description="If true, treat pattern as a regular expression.",
    )


class TruncateRequest(BaseModel):
    """Payload for truncate-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    max_length: int = Field(
        default=80,
        ge=5,
        le=1000,
        description="Maximum character length per line.",
    )


class NthLineRequest(BaseModel):
    """Payload for extract-nth-lines requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    n: int = Field(
        default=2,
        ge=2,
        le=100,
        description="Extract every Nth line.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting line offset (0-indexed).",
    )


class CaesarRequest(BaseModel):
    """Payload for Caesar cipher requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    shift: int = Field(
        default=3,
        ge=1,
        le=25,
        description="Number of positions to shift each letter.",
    )


class RailFenceRequest(BaseModel):
    """Payload for Rail Fence cipher requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    rails: int = Field(
        default=3,
        ge=2,
        le=10,
        description="Number of rails for the cipher.",
    )


class KeyedCipherRequest(BaseModel):
    """Payload for cipher requests that require a key (Vigenere, Playfair, etc.)."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The cipher key or passphrase.",
    )


class SubstitutionRequest(BaseModel):
    """Payload for substitution cipher requests."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The input text to be processed.",
    )
    mapping: str = Field(
        ...,
        min_length=26,
        max_length=26,
        description="26-character substitution alphabet (A-Z mapping).",
    )


class TextResponse(BaseModel):
    """Transformed text returned by the API."""

    original: str = Field(..., description="The original input text.")
    result: str = Field(..., description="The transformed output text.")
    operation: str = Field(..., description="Name of the operation performed.")

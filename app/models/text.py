"""Pydantic models (schemas) for text-processing requests and responses."""

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


class TextResponse(BaseModel):
    """Transformed text returned by the API."""

    original: str = Field(..., description="The original input text.")
    result: str = Field(..., description="The transformed output text.")
    operation: str = Field(..., description="Name of the operation performed.")


class TextAnalysisResponse(BaseModel):
    """Statistical summary of the provided text."""

    text: str = Field(..., description="The analysed input text.")
    word_count: int
    sentence_count: int
    character_count: int
    character_count_no_spaces: int
    reading_time_minutes: float = Field(
        ..., description="Estimated reading time at 125 wpm."
    )

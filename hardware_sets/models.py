"""Public extraction contract shared by the parser, CLI, and review application."""

from __future__ import annotations

from math import isfinite
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvidenceModel(BaseModel):
    # Additional evidence can be attached without making saved results unreadable.
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)


class Location(EvidenceModel):
    """Top-left-origin PDF points; page is a one-based physical PDF page."""

    page: int = Field(ge=1)
    bbox: list[float] = Field(min_length=4, max_length=4)
    page_width: float = Field(gt=0)
    page_height: float = Field(gt=0)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @field_validator("bbox")
    @classmethod
    def valid_box(cls, value: list[float]) -> list[float]:
        if not all(isfinite(n) for n in value):
            raise ValueError("Bounding-box coordinates must be finite")
        if value[2] < value[0] or value[3] < value[1]:
            raise ValueError("Bounding box must be [left, top, right, bottom]")
        return value

    @model_validator(mode="after")
    def ordered_lines(self) -> Location:
        if self.line_start is not None and self.line_end is not None:
            if self.line_end < self.line_start:
                raise ValueError("line_end must be at least line_start")
        return self


class CatalogResolution(EvidenceModel):
    """Evidence-backed expansion of a shorthand code printed on the same page."""

    code: str
    description: str | None = None
    catalog_number: str | None = None
    mfr: str | None = None
    finish: str | None = None
    notes: str | None = None
    location: Location
    confidence: float = Field(default=0.0, ge=0, le=1)


class Component(EvidenceModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    qty: float | str | None = None
    description: str = ""
    catalog_number: str | None = None
    mfr: str | None = None
    finish: str | None = None
    notes: str | None = None
    confidence: dict[str, float] = Field(default_factory=dict)
    locations: list[Location] = Field(default_factory=list)
    raw_text: str = ""
    warnings: list[str] = Field(default_factory=list)
    catalog_resolution: CatalogResolution | None = None

    @field_validator("confidence")
    @classmethod
    def bounded_confidence(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not 0 <= score <= 1 for score in value.values()):
            raise ValueError("Confidence scores must be between zero and one")
        return value


class HardwareSet(EvidenceModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    set_number: str
    description: str | None = None
    status: Literal["active", "not_used"] = "active"
    locations: list[Location] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    corrected: bool = False


class ExtractionResult(EvidenceModel):
    schema_version: str = "1.0"
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = ""
    project: str | None = None
    page_count: int = Field(default=0, ge=0)
    sets: list[HardwareSet] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)

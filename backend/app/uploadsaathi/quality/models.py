"""What the validator concluded about the finished document."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

QualityStatus = Literal["unchanged", "passed", "degraded", "failed"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Per-rule verdicts, so the UI can tell the citizen exactly what is wrong."""

    is_valid: bool
    quality_status: QualityStatus
    readable: bool
    size_valid: bool
    format_valid: bool
    dimensions_valid: bool
    pages_valid: bool
    colour_valid: bool
    issues: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

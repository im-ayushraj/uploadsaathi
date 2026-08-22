"""What the engine produces after executing a plan."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OptimizedDocument:
    """The result of running an OptimizationPlan over real bytes.

    A failure is data, not an exception: `succeeded=False` plus `failure_reason`.
    """

    data: bytes
    detected_format: str
    kind: str
    byte_size: int
    original_byte_size: int
    succeeded: bool = True
    failure_reason: str | None = None
    target_met: bool = False

    width: int | None = None
    height: int | None = None
    pages: int | None = None

    steps_applied: tuple[str, ...] = field(default_factory=tuple)
    quality_used: int | None = None
    scale_applied: float = 1.0
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def reduction_percent(self) -> float:
        if not self.original_byte_size:
            return 0.0
        saved = self.original_byte_size - self.byte_size
        return round(saved / self.original_byte_size * 100, 1)

    @property
    def changed(self) -> bool:
        return bool(self.steps_applied)

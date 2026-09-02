# Copyright 2026 PSI Tool contributors
"""Typed cache boundary failures."""

from typing import ClassVar, final, override


@final
class CacheIntegrityError(ValueError):
    """Cache content does not match its trusted identity contract."""

    __slots__: ClassVar[tuple[str, ...]] = ("detail",)
    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    @override
    def __str__(self) -> str:
        return self.detail


@final
class CachePathError(ValueError):
    """Descriptor-owned cache contains foreign or unsafe state."""

    __slots__: ClassVar[tuple[str, ...]] = ("detail",)
    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    @override
    def __str__(self) -> str:
        return self.detail

# Copyright 2026 PSI Tool contributors
"""Controlled POSIX cancellation for the PSI CLI boundary."""

from __future__ import annotations

import signal
from contextlib import contextmanager
from typing import TYPE_CHECKING, ClassVar, final, override

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import FrameType


@final
class InspectCancelled(BaseException):
    """Typed cancellation raised by the main-thread signal handler."""

    __slots__: ClassVar[tuple[str, ...]] = ("signum",)
    signum: int

    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(signum)

    @property
    def exit_code(self) -> int:
        return 130 if self.signum == signal.SIGINT else 143

    @override
    def __str__(self) -> str:
        return "inspect cancelled"


@final
class _SignalHandler:
    __slots__ = ("_deferred", "_pending")

    def __init__(self) -> None:
        self._deferred = False
        self._pending: int | None = None

    def __call__(self, signum: int, _frame: FrameType | None) -> None:
        if self._deferred:
            if self._pending is None:
                self._pending = signum
            return
        raise InspectCancelled(signum)

    @contextmanager
    def deferred(self) -> Generator[None]:
        """Record cancellation until the protected value is caller-visible."""
        self._deferred = True
        try:
            yield
        finally:
            self._deferred = False
            pending = self._pending
            self._pending = None
            if pending is not None:
                raise InspectCancelled(pending)


@contextmanager
def controlled_signals() -> Generator[_SignalHandler]:
    """Raise typed cancellation for the first SIGINT or SIGTERM."""
    handler = _SignalHandler()
    previous_int = signal.signal(signal.SIGINT, handler)
    previous_term = signal.signal(signal.SIGTERM, handler)
    try:
        yield handler
    finally:
        _ = signal.signal(signal.SIGINT, previous_int)
        _ = signal.signal(signal.SIGTERM, previous_term)


@contextmanager
def signals_ignored() -> Generator[None]:
    """Prevent later signals from interrupting cleanup or atomic publication."""
    previous_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
    previous_term = signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        yield
    finally:
        _ = signal.signal(signal.SIGINT, previous_int)
        _ = signal.signal(signal.SIGTERM, previous_term)

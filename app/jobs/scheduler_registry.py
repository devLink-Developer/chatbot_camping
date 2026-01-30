"""
Central registry for scheduler-ready callables.
"""

from __future__ import annotations

from typing import Callable, Dict

_JOBS: Dict[str, Callable[..., object]] = {}


def register_job(name: str, func: Callable[..., object]) -> None:
    """Register a callable under a unique name."""
    _JOBS[name] = func


def get_job(name: str) -> Callable[..., object]:
    """Return a registered callable by name."""
    return _JOBS[name]


def list_jobs() -> Dict[str, Callable[..., object]]:
    """Return a copy of the current registry."""
    return dict(_JOBS)

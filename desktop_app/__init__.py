"""Desktop GUI application for the Zenith sensor helper."""

from __future__ import annotations

__all__ = ["run"]


def run() -> None:
    """Launch the desktop helper application."""
    from desktop_app.app import run as _run
    _run()



"""Configuration helpers for the Zenith Tek sensor helper service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 7421
DEFAULT_BAUD_RATE: Final[int] = 460_800
DEFAULT_DATA_DIR: Final[Path] = Path.home() / ".zenith_helper"
DEFAULT_UPDATES_DIR: Final[Path] = DEFAULT_DATA_DIR / "updates"
DEFAULT_UPDATE_POLL_INTERVAL: Final[int] = 6 * 60 * 60  # 6 hours
DEFAULT_ALLOWED_ORIGINS: Final[list[str]] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
]

TOKEN_ENV_KEY: Final[str] = "ZENITH_HELPER_TOKEN"
TOKEN_FILE: Final[Path] = Path.home() / ".zenith_helper_token"

SUPABASE_URL_ENV: Final[str] = "ZENITH_SUPABASE_URL"
SUPABASE_ANON_KEY_ENV: Final[str] = "ZENITH_SUPABASE_ANON_KEY"
UPDATES_DIR_ENV: Final[str] = "ZENITH_HELPER_UPDATES_DIR"
UPDATE_POLL_ENV: Final[str] = "ZENITH_HELPER_UPDATE_POLL_INTERVAL"
ALLOWED_ORIGINS_ENV: Final[str] = "ZENITH_HELPER_ALLOWED_ORIGINS"


@dataclass(frozen=True)
class HelperSettings:
    """Runtime configuration for the helper service."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    default_baud_rate: int = DEFAULT_BAUD_RATE
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    log_level: str = "INFO"
    updates_dir: Path = DEFAULT_UPDATES_DIR
    update_poll_interval: int = DEFAULT_UPDATE_POLL_INTERVAL
    allowed_origins: list[str] = field(default_factory=lambda: [origin for origin in DEFAULT_ALLOWED_ORIGINS])

    @classmethod
    def from_env(cls) -> "HelperSettings":
        """Create settings by reading environment variables."""
        load_dotenv()
        updates_dir = Path(os.getenv(UPDATES_DIR_ENV, str(DEFAULT_UPDATES_DIR))).expanduser()
        try:
            poll_interval = int(os.getenv(UPDATE_POLL_ENV, DEFAULT_UPDATE_POLL_INTERVAL))
        except ValueError:
            poll_interval = DEFAULT_UPDATE_POLL_INTERVAL
        if poll_interval < 60:
            poll_interval = 60
        origins_env = os.getenv(ALLOWED_ORIGINS_ENV, "")
        if origins_env.strip():
            origins = [origin.strip().rstrip("/") for origin in origins_env.split(",") if origin.strip()]
        else:
            origins = [origin.rstrip("/") for origin in DEFAULT_ALLOWED_ORIGINS]
        return cls(
            host=os.getenv("ZENITH_HELPER_HOST", DEFAULT_HOST),
            port=int(os.getenv("ZENITH_HELPER_PORT", DEFAULT_PORT)),
            default_baud_rate=int(os.getenv("ZENITH_HELPER_BAUD", DEFAULT_BAUD_RATE)),
            supabase_url=os.getenv(SUPABASE_URL_ENV),
            supabase_anon_key=os.getenv(SUPABASE_ANON_KEY_ENV),
            log_level=os.getenv("ZENITH_HELPER_LOG_LEVEL", "INFO"),
            updates_dir=updates_dir,
            update_poll_interval=poll_interval,
            allowed_origins=origins,
        )


def ensure_token() -> str:
    """Return the auth token, generating it if necessary."""
    token = os.getenv(TOKEN_ENV_KEY)
    if token:
        return token

    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()

    import secrets

    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    os.chmod(TOKEN_FILE, 0o600)
    return token



"""Entry point for running the helper service."""

from __future__ import annotations

import uvicorn  # type: ignore

from helper_app.api import create_app
from helper_app.config import HelperSettings, ensure_token


def main() -> None:  # pragma: no cover - runtime entry
    settings = HelperSettings.from_env()
    token = ensure_token()
    print(f"Zenith Helper starting on http://{settings.host}:{settings.port}")
    print("API token stored at ~/.zenith_helper_token")
    print(f"Current token: {token}")
    app = create_app()
    uvicorn_level = settings.log_level.lower()
    if uvicorn_level not in {"trace", "debug", "info", "warning", "error", "critical"}:
        uvicorn_level = "info"
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=uvicorn_level)


if __name__ == "__main__":  # pragma: no cover
    main()


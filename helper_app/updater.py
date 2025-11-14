"""Auto-update helper using Supabase manifests."""

from __future__ import annotations

import logging
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import platform

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None

LOG = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    checksum: Optional[str] = None
    release_notes: Optional[str] = None


@dataclass
class DownloadResult:
    version: str
    path: Path
    bytes_downloaded: int
    checksum_verified: Optional[bool] = None


async def check_for_updates(
    supabase_url: str, anon_key: str, current_version: str, platform_name: str | None = None
) -> Optional[UpdateInfo]:
    if httpx is None:
        LOG.debug("httpx not installed; skipping update check")
        return None

    headers = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    detected_platform = platform_name or platform.system().lower()
    if detected_platform.startswith("win"):
        detected_platform = "windows"
    elif detected_platform.startswith("darwin") or detected_platform.startswith("mac"):
        detected_platform = "macos"
    elif detected_platform.startswith("linux"):
        detected_platform = "linux"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/helper_updates",
                params={
                    "select": "*",
                    "order": "version.desc",
                    "limit": 1,
                    "platform": f"eq.{detected_platform}",
                },
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # pragma: no cover - network errors
        LOG.warning("Update check failed: %s", exc)
        return None

    if not data:
        return None

    latest = data[0]
    latest_version = latest.get("version")
    if not latest_version or latest_version <= current_version:
        return None

    return UpdateInfo(
        version=latest_version,
        download_url=latest.get("download_url"),
        checksum=latest.get("checksum"),
        release_notes=latest.get("release_notes"),
    )


def _derive_filename(update: UpdateInfo) -> str:
    parsed = urlparse(update.download_url)
    candidate = Path(parsed.path).name
    if candidate:
        return candidate
    return f"zenith-helper-{update.version}.bin"


def _resolve_target_path(directory: Path, filename: str, version: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    base_path = directory / filename
    if not base_path.exists():
        return base_path

    stem = Path(filename).stem or "zenith-helper"
    suffix = Path(filename).suffix
    candidate = directory / f"{stem}-{version}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{version}-{counter}{suffix}"
        counter += 1
    return candidate


async def download_update(update: UpdateInfo, target_dir: Path) -> DownloadResult:
    """Download the helper update and verify checksum if provided."""
    if httpx is None:
        raise RuntimeError("httpx dependency not available; cannot download update")

    filename = _derive_filename(update)
    target_path = _resolve_target_path(target_dir, filename, update.version)
    temp_path = target_path.with_name(target_path.name + ".part")

    hasher = hashlib.sha256() if update.checksum else None
    bytes_downloaded = 0

    try:
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            async with client.stream("GET", update.download_url) as response:
                response.raise_for_status()
                with temp_path.open("wb") as outfile:
                    async for chunk in response.aiter_bytes():
                        if not chunk:
                            continue
                        outfile.write(chunk)
                        bytes_downloaded += len(chunk)
                        if hasher is not None:
                            hasher.update(chunk)

        checksum_verified: Optional[bool] = None
        if hasher is not None and update.checksum:
            digest = hasher.hexdigest()
            checksum_verified = digest.lower() == update.checksum.lower()
            if not checksum_verified:
                temp_path.unlink(missing_ok=True)
                raise ValueError("Checksum mismatch for downloaded update")

        temp_path.replace(target_path)
        return DownloadResult(
            version=update.version,
            path=target_path,
            bytes_downloaded=bytes_downloaded,
            checksum_verified=checksum_verified if update.checksum else None,
        )
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


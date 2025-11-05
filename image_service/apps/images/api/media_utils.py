from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

from django.conf import settings
from django.utils._os import safe_join


class MediaAsset(NamedTuple):
    path: Path
    is_placeholder: bool


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen = set()
    unique: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        unique.append(resolved)
        seen.add(resolved)
    return unique


def get_media_search_paths() -> list[Path]:
    """Ordered list of directories where original image files might live."""
    configured = getattr(settings, "MEDIA_FALLBACK_DIRS", None) or ()
    env_override = os.environ.get("SHOTDECK_MEDIA_FALLBACK_DIRS", "")
    env_paths = [p.strip() for p in env_override.split(os.pathsep) if p.strip()]

    candidates = [
        Path(settings.MEDIA_ROOT),
        *[Path(p) for p in configured],
        *[Path(p) for p in env_paths],
        Path("/host_data/shot_images"),
        Path("/host_data/shotdeck/shot_images"),
        Path("/host_data/media/images"),
        Path("/host_data"),
    ]
    return _unique_paths(candidates)


def resolve_media_path(relative_path: str) -> Optional[Path]:
    """Attempt to locate the requested media file across all search paths."""
    relative = Path(relative_path.strip("/"))
    if relative.is_absolute():
        relative = Path(*relative.parts[1:])

    for base in get_media_search_paths():
        candidate = base / relative
        if candidate.exists():
            return candidate

        filename = relative.name
        for variation in (filename, filename.upper(), filename.lower()):
            candidate_flat = base / variation
            if candidate_flat.exists():
                return candidate_flat
    return None


JPEG_PLACEHOLDER = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhUTEhIVFhUVFRUVFRYVFRcVFRUWFhUVFRUYHSggGBolHRUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGhAQGy0lHyYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKMBNwMBIgACEQEDEQH/xAAUAAEAAAAAAAAAAAAAAAAAAAAJ/8QAFxABAQEBAAAAAAAAAAAAAAAAAQIDAP/EABUBAQEAAAAAAAAAAAAAAAAAAAAB/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8A9QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/2Q=="
)

PNG_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8HwQACfsD/Q8aBwAAAABJRU5ErkJggg=="
)

GIF_PLACEHOLDER = base64.b64decode(
    "R0lGODlhAQABAPAAAAAAAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
)


def _placeholder_bytes(extension: str) -> bytes:
    ext = extension.lower()
    if ext in {".jpg", ".jpeg", ".webp"}:
        return JPEG_PLACEHOLDER
    if ext == ".gif":
        return GIF_PLACEHOLDER
    return PNG_PLACEHOLDER


def _marker_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + '.placeholder')


def _mark_placeholder(target: Path) -> None:
    try:
        marker = _marker_path(target)
        marker.touch(exist_ok=True)
    except OSError:
        pass


def _clear_placeholder_marker(target: Path) -> None:
    marker = _marker_path(target)
    try:
        if marker.exists():
            marker.unlink()
    except OSError:
        pass


def _is_placeholder_file(target: Path) -> bool:
    marker = _marker_path(target)
    if marker.exists():
        return True
    try:
        size = target.stat().st_size
    except OSError:
        return False
    placeholder_sizes = {len(JPEG_PLACEHOLDER), len(PNG_PLACEHOLDER), len(GIF_PLACEHOLDER)}
    if size in placeholder_sizes:
        try:
            data = target.read_bytes()
        except OSError:
            return False
        return data in {JPEG_PLACEHOLDER, PNG_PLACEHOLDER, GIF_PLACEHOLDER}
    return False


def _write_placeholder(target: Path) -> MediaAsset:
    target.parent.mkdir(parents=True, exist_ok=True)
    placeholder_data = _placeholder_bytes(target.suffix or ".png")
    try:
        target.write_bytes(placeholder_data)
    except OSError:
        shared = Path(settings.MEDIA_ROOT) / "placeholder_fallback.png"
        if not shared.exists():
            shared.parent.mkdir(parents=True, exist_ok=True)
            shared.write_bytes(PNG_PLACEHOLDER)
        return MediaAsset(shared, True)
    _mark_placeholder(target)
    return MediaAsset(target, True)


def ensure_media_local(relative_path: str) -> Optional[MediaAsset]:
    """
    Ensure the requested media file is available beneath MEDIA_ROOT.
    If found elsewhere it is copied locally; otherwise a placeholder is generated.
    Returns a MediaAsset describing the resolved path and whether it is a placeholder.
    """
    relative = Path(relative_path.strip("/"))
    try:
        target = Path(safe_join(settings.MEDIA_ROOT, str(relative)))
    except ValueError:
        return None

    if target.exists():
        return MediaAsset(target, _is_placeholder_file(target))

    original = resolve_media_path(str(relative))
    if original:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(original, target)
            _clear_placeholder_marker(target)
            return MediaAsset(target, False)
        except OSError:
            return MediaAsset(original, False)

    return _write_placeholder(target)

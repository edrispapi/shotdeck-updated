from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from typing import Iterable, NamedTuple, Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.utils._os import safe_join


class MediaAsset(NamedTuple):
    path: Path
    is_placeholder: bool


JPEG_PLACEHOLDER = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhUTEhIVFhUVFRUVFRYVFRcVFRUWFhUVFRUYHSggGBolHRUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGhAQGy0lHyYtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKMBNwMBIgACEQEDEQH/xAAUAAEAAAAAAAAAAAAAAAAAAAAJ/8QAFxABAQEBAAAAAAAAAAAAAAAAAQIDAP/EABUBAQEAAAAAAAAAAAAAAAAAAAAB/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8A9QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/2Q=="
)

PNG_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8HwQACfsD/Q8aBwAAAABJRU5ErkJggg=="
)

GIF_PLACEHOLDER = base64.b64decode(
    "R0lGODlhAQABAPAAAAAAAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
)


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

    base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    sibling_media_root = base_dir.parent / "shotdeck-media"
    upstream_media_root = base_dir.parent.parent / "shotdeck-media"
    sibling_media_roots = {
        sibling_media_root,
        upstream_media_root,
    }
    local_candidates = [
        base_dir / "media",
        base_dir / "media" / "images",
        *(
            candidate
            for root in sibling_media_roots
            for candidate in (
                root,
                root / "media",
                root / "media" / "images",
            )
        ),
    ]

    candidates = [
        Path(settings.MEDIA_ROOT),
        *[Path(p) for p in configured],
        *[Path(p) for p in env_paths],
        *local_candidates,
        Path("/host_data/shot_images"),
        Path("/host_data/shotdeck/shot_images"),
        Path("/host_data/media/images"),
        Path("/host_data"),
    ]
    return _unique_paths(candidates)


def resolve_media_path(relative_path: str, *, exclude: Iterable[Path] | None = None) -> Optional[Path]:
    """
    Attempt to locate the requested media file across all search paths.
    Optionally skip any paths present in ``exclude`` (resolved).
    """
    relative = Path(relative_path.strip("/"))
    if relative.is_absolute():
        relative = Path(*relative.parts[1:])

    excluded: set[Path] = set()
    if exclude:
        for path in exclude:
            try:
                excluded.add(path.resolve())
            except OSError:
                continue

    for base in get_media_search_paths():
        candidate = base / relative
        try:
            resolved_candidate = candidate.resolve()
        except OSError:
            resolved_candidate = candidate

        if resolved_candidate in excluded:
            continue

        if candidate.exists():
            return candidate

        filename = relative.name
        for variation in (filename, filename.upper(), filename.lower()):
            candidate_flat = base / variation
            try:
                resolved_flat = candidate_flat.resolve()
            except OSError:
                resolved_flat = candidate_flat

            if resolved_flat in excluded:
                continue

            if candidate_flat.exists():
                return candidate_flat
    return None


def _placeholder_bytes(extension: str) -> bytes:
    ext = extension.lower()
    if ext in {".jpg", ".jpeg", ".webp"}:
        return JPEG_PLACEHOLDER
    if ext == ".gif":
        return GIF_PLACEHOLDER
    return PNG_PLACEHOLDER


def _marker_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".placeholder")


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
        if target.exists():
            try:
                size = target.stat().st_size
            except OSError:
                return True
            placeholder_sizes = {len(JPEG_PLACEHOLDER), len(PNG_PLACEHOLDER), len(GIF_PLACEHOLDER)}
            if size not in placeholder_sizes:
                try:
                    marker.unlink()
                except OSError:
                    pass
                return False
            try:
                data = target.read_bytes()
            except OSError:
                return True
            if data not in {JPEG_PLACEHOLDER, PNG_PLACEHOLDER, GIF_PLACEHOLDER}:
                try:
                    marker.unlink()
                except OSError:
                    pass
                return False
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
        placeholder_local = _is_placeholder_file(target)
        if placeholder_local:
            original = resolve_media_path(str(relative), exclude={target})
            if original and original != target and not _is_placeholder_file(original):
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, target)
                    _clear_placeholder_marker(target)
                    return MediaAsset(target, False)
                except OSError:
                    return MediaAsset(original, False)
        return MediaAsset(target, placeholder_local)

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


def extract_media_relative_path(image_url: Optional[str]) -> Optional[str]:
    """
    Return the relative path beneath MEDIA_ROOT for a given image URL or path.
    Handles absolute URLs pointing to /media/, root-relative and bare paths.
    """
    if not image_url:
        return None

    raw = image_url.strip()
    if not raw:
        return None

    parsed = urlparse(raw) if raw.startswith(('http://', 'https://', '//')) else None

    if parsed:
        # Join scheme for protocol-relative URLs
        if not parsed.scheme and raw.startswith('//'):
            parsed = urlparse(f"http:{raw}")
        path = parsed.path or ""
        if '/media/' not in path:
            return None
        relative = path.split('/media/', 1)[1]
    else:
        relative = raw.lstrip('/')
        if relative.startswith('media/'):
            relative = relative.split('media/', 1)[1]

    relative = relative.lstrip('/')
    return relative or None


def resolve_media_reference(image_url: Optional[str]) -> Tuple[Optional[str], Optional[MediaAsset]]:
    """
    Attempt to resolve the provided image URL/path to a local MediaAsset.
    Returns a tuple of (relative_path, MediaAsset). If the URL points to an
    external resource, both values will be None.
    """
    relative = extract_media_relative_path(image_url)
    if not relative:
        return None, None

    asset = ensure_media_local(relative)
    if asset and "placeholder" in Path(relative).name.lower():
        asset = MediaAsset(asset.path, True)
    return relative, asset


# --------------------------------------------------------------------------- #
#  Convenience helpers for slug/code-based lookups
# --------------------------------------------------------------------------- #
VALID_IMAGE_EXTS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def find_asset_for_slug(slug: str) -> Tuple[Optional[str], Optional[MediaAsset]]:
    """
    Try to locate a non-placeholder asset for a given image code/slug.
    Returns (relative_path, MediaAsset) when found; otherwise (None, None).
    """
    if not slug:
        return None, None

    code_candidates = [slug, slug.upper(), slug.lower()]
    for code in code_candidates:
        for ext in VALID_IMAGE_EXTS:
            relative = f"images/{code}{ext}"
            path = resolve_media_path(relative)
            if not path:
                continue
            # Skip placeholders
            if _is_placeholder_file(path):
                continue
            # Ensure under MEDIA_ROOT and return
            asset = ensure_media_local(relative)
            if asset and not asset.is_placeholder:
                return relative, asset
    return None, None

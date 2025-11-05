from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.images.api.media_utils import get_media_search_paths
from apps.images.models import Image


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MIN_REAL_IMAGE_BYTES = 1024  # smaller files are treated as placeholders
PLACEHOLDER_FILENAME = "placeholder_missing.png"


def _iter_source_directories(override_dirs: Iterable[str]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []

    def _add(candidate: Path) -> None:
        candidate = candidate.resolve()
        if candidate in seen:
            return
        if candidate.exists() and candidate.is_dir():
            ordered.append(candidate)
            seen.add(candidate)

    media_root = Path(settings.MEDIA_ROOT)
    _add(media_root / "images")
    for path in get_media_search_paths():
        _add(path)
    for override in override_dirs:
        if override:
            _add(Path(override))
    return ordered


@dataclass
class ResyncStats:
    matched: int = 0
    copied: int = 0
    updated: int = 0
    cleared: int = 0
    missing: int = 0


class Command(BaseCommand):
    help = (
        "Rebuild image_url fields to match actual files on disk. "
        "Copies assets into MEDIA_ROOT when found in fallback directories and "
        "clears outdated URLs when files are missing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            action="append",
            dest="source_dirs",
            default=[],
            help="Additional directories to search for shot images",
        )
        parser.add_argument(
            "--remove-missing",
            action="store_true",
            help="Clear image_url when no matching asset is found",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report intended changes without modifying the database or filesystem",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of images processed (useful for testing)",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        remove_missing: bool = options["remove_missing"]
        limit: int | None = options.get("limit")

        search_dirs = _iter_source_directories(options["source_dirs"])
        media_images_dir = Path(settings.MEDIA_ROOT) / "images"
        media_images_dir.mkdir(parents=True, exist_ok=True)
        placeholder_url = self._ensure_placeholder_asset(media_images_dir)

        self.stdout.write(
            f"Scanning source directories: {', '.join(str(p) for p in search_dirs)}"
        )
        asset_index = self._build_asset_index(search_dirs)
        self.stdout.write(f"Indexed {len(asset_index)} candidate files")
        self.asset_index = asset_index

        queryset = Image.objects.order_by("id")
        if limit:
            queryset = queryset[:limit]

        stats = ResyncStats()
        total = queryset.count() if limit is None else limit

        for index, image in enumerate(queryset.iterator(), start=1):
            asset_path = self._locate_asset(image.slug)

            if asset_path and asset_path.exists() and asset_path.stat().st_size > MIN_REAL_IMAGE_BYTES:
                stats.matched += 1

                destination = media_images_dir / asset_path.name
                if destination != asset_path:
                    if not dry_run:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(asset_path, destination)
                    stats.copied += 1

                new_url = f"/media/images/{destination.name}"
                if image.image_url != new_url:
                    stats.updated += 1
                    if not dry_run:
                        image.image_url = new_url
                        image.save(update_fields=["image_url", "updated_at"])
            else:
                stats.missing += 1
                if remove_missing:
                    stats.cleared += 1
                    if not dry_run:
                        image.image_url = placeholder_url
                        image.save(update_fields=["image_url", "updated_at"])

            if index % 250 == 0 or index == total:
                self.stdout.write(
                    f"Processed {index}/{total} images... matched={stats.matched} missing={stats.missing}"
                )

        summary = (
            f"Resync complete. matched={stats.matched}, copied={stats.copied}, "
            f"updated={stats.updated}, cleared={stats.cleared}, missing={stats.missing}"
        )
        if dry_run:
            summary = "[dry-run] " + summary
        self.stdout.write(self.style.SUCCESS(summary))

    def _build_asset_index(self, directories: Iterable[Path]) -> dict[str, Path]:
        index: dict[str, Path] = {}
        for directory in directories:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in directory.iterdir():
                if not path.is_file():
                    continue
                if path.suffix.lower() not in VALID_EXTENSIONS:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size < MIN_REAL_IMAGE_BYTES:
                    continue
                key = path.stem.lower()
                if key not in index:
                    index[key] = path
        return index

    def _locate_asset(self, slug: str) -> Path | None:
        return getattr(self, "asset_index", {}).get(slug.lower())

    def _ensure_placeholder_asset(self, media_images_dir: Path) -> str:
        placeholder_path = media_images_dir / PLACEHOLDER_FILENAME
        if not placeholder_path.exists():
            placeholder_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                placeholder_path.write_bytes(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\xd7c``````\x00\x00\x00\x06\x00\x02"
                    b"J|\x8d\xc4\x00\x00\x00\x00IEND\xaeB`\x82"
                )
            except OSError:
                pass
        return f"/media/images/{PLACEHOLDER_FILENAME}"

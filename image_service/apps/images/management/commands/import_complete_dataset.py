import logging
from typing import List

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from apps.images.models import (
    Image,
    Movie,
    Tag,
    ColorOption,
)


logger = logging.getLogger(__name__)


STAGE_ORDER = [
    # Import images that have matching JSON metadata and files
    "import_images_with_metadata",
    # Populate release_year from YearOption and Movie.year
    "backfill_release_year",
    # Backfill color directly from JSON shot_info.color (if available)
    "backfill_colors",
    # Derive color from shade hex buckets
    "derive_colors_from_shades",
    # Extract tags from description into Image.tags
    "normalize_image_tags",
    # Populate Movie.crew fields and image_count
    "populate_movie_fields",
]


class Command(BaseCommand):
    help = "Run a complete, orchestrated import for images and movies, including backfills and fixes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-dir",
            type=str,
            default="/host_data/dataset/shot_json_data",
            help="Path to JSON files directory used by relevant subcommands.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of items processed by import/backfill commands where supported.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run commands in dry-run mode where supported.",
        )
        parser.add_argument(
            "--skip-missing-files",
            action="store_true",
            help="Skip JSONs whose image files are missing (passed to import when supported).",
        )
        parser.add_argument(
            "--stages",
            type=str,
            help=(
                "Comma-separated list of stages to run. Available: "
                + ", ".join(STAGE_ORDER)
            ),
        )

    def handle(self, *args, **options):
        json_dir = options.get("json_dir")
        limit = options.get("limit")
        dry_run = options.get("dry_run")
        skip_missing = options.get("skip_missing_files")
        stages_arg = options.get("stages")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )

        stages: List[str] = STAGE_ORDER
        if stages_arg:
            requested = [s.strip() for s in stages_arg.split(",") if s.strip()]
            unknown = [s for s in requested if s not in STAGE_ORDER]
            if unknown:
                raise CommandError(f"Unknown stage(s): {', '.join(unknown)}")
            stages = requested

        self.stdout.write("Starting complete dataset import orchestration\n")
        self._print_snapshot("Before")

        for stage in stages:
            self.stdout.write(f"\n--- Stage: {stage} ---")
            try:
                if stage == "import_images_with_metadata":
                    # Primary import that only imports records with valid JSON + image file
                    kwargs = {
                        "json_dir": json_dir,
                    }
                    if dry_run:
                        kwargs["dry_run"] = True
                    if limit is not None:
                        kwargs["limit"] = limit
                    # Support optional --skip-missing-files if implemented in optimized command
                    # Prefer import_images_with_metadata; if not sufficient, allow optimized variant via stages
                    call_command("import_images_with_metadata", **kwargs)

                elif stage == "backfill_release_year":
                    kwargs = {}
                    if dry_run:
                        kwargs["dry_run"] = True
                    call_command("backfill_release_year", **kwargs)

                elif stage == "backfill_colors":
                    kwargs = {
                        "json_dir": json_dir,
                    }
                    if dry_run:
                        kwargs["dry_run"] = True
                    if limit is not None:
                        kwargs["limit"] = limit
                    call_command("backfill_colors", **kwargs)

                elif stage == "derive_colors_from_shades":
                    kwargs = {}
                    if dry_run:
                        kwargs["dry_run"] = True
                    call_command("derive_colors_from_shades", **kwargs)

                elif stage == "normalize_image_tags":
                    kwargs = {}
                    if dry_run:
                        kwargs["dry_run"] = True
                    call_command("normalize_image_tags", **kwargs)

                elif stage == "populate_movie_fields":
                    kwargs = {}
                    if dry_run:
                        kwargs["dry_run"] = True
                    call_command("populate_movie_fields", **kwargs)

                else:
                    raise CommandError(f"Unhandled stage: {stage}")
            except Exception as exc:
                logger.exception("Stage %s failed: %s", stage, exc)
                if dry_run:
                    # Continue in dry-run to collect more feedback
                    continue
                # In non-dry-run mode, fail fast
                raise

        self.stdout.write("\nAll stages finished\n")
        self._print_snapshot("After")

    def _print_snapshot(self, label: str):
        images = Image.objects.count()
        movies = Movie.objects.count()
        tags = Tag.objects.count()
        colors = ColorOption.objects.count()
        self.stdout.write(
            f"{label} snapshot -> images: {images}, movies: {movies}, tags: {tags}, colors: {colors}"
        )




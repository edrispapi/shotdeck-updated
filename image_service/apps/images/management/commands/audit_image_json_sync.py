from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError

from apps.images.models import Image


class Command(BaseCommand):
    help = "Compare database image slugs with JSON filenames to find mismatches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-dir",
            default="/host_data/shot_json_data",
            help="Directory containing shot JSON files (default: /host_data/shot_json_data)",
        )
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Optional directory to write db_only.txt and json_only.txt reports",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="How many mismatches to show in console output (default: 20)",
        )

    def handle(self, *args, **options):
        json_dir = Path(options["json_dir"])
        output_dir = options["output_dir"]
        limit = max(1, options["limit"] or 20)

        if not json_dir.exists() or not json_dir.is_dir():
            raise CommandError(f"JSON directory not found: {json_dir}")

        db_slugs = set(Image.objects.values_list("slug", flat=True))
        json_ids = {
            Path(name).stem.lower()
            for name in os.listdir(json_dir)
            if name.endswith(".json")
        }

        db_only = sorted(db_slugs - json_ids)
        json_only = sorted(json_ids - db_slugs)
        overlap = len(db_slugs & json_ids)

        self.stdout.write(self.style.SUCCESS("Comparison complete"))
        self.stdout.write(f"  DB slugs   : {len(db_slugs)}")
        self.stdout.write(f"  JSON files : {len(json_ids)}")
        self.stdout.write(f"  Intersection: {overlap}")
        self.stdout.write(f"  DB-only    : {len(db_only)}")
        self.stdout.write(f"  JSON-only  : {len(json_only)}")

        def _preview(items: Iterable[str], label: str):
            items = list(items)
            if not items:
                self.stdout.write(f"  {label}: none")
                return
            preview = items[:limit]
            remainder = len(items) - len(preview)
            suffix = f" … (+{remainder})" if remainder > 0 else ""
            self.stdout.write(f"  {label}: {', '.join(preview)}{suffix}")

        _preview(db_only, "DB missing JSON")
        _preview(json_only, "JSON missing DB")

        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / "db_only.txt").write_text("\n".join(db_only), encoding="utf-8")
            (out_path / "json_only.txt").write_text("\n".join(json_only), encoding="utf-8")
            self.stdout.write(f"Reports written to {out_path}")

from __future__ import annotations

import math
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand

from apps.images.models import Image


class Command(BaseCommand):
    help = "Verify that image_url values resolve to existing remote assets and match Image.slug"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of Image rows to check (default: all)",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of initial rows to skip before checking",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=200,
            help="Database iterator chunk size (default: 200)",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=5.0,
            help="HTTP timeout in seconds for each request (default: 5)",
        )
        parser.add_argument(
            "--method",
            choices=["head", "get"],
            default="head",
            help="Primary HTTP method to use (default: HEAD, falls back to GET on 405/>=400)",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop on first failure instead of scanning all rows",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        offset = max(0, options["offset"])
        chunk_size = max(50, options["chunk_size"])
        timeout = options["timeout"]
        primary_method = options["method"]
        fail_fast = options["fail_fast"]

        qs = Image.objects.order_by("slug")
        total = qs.count()
        if offset:
            qs = qs[offset:]
        if limit is not None:
            qs = qs[:limit]

        checked = 0
        http_failures: list[str] = []
        slug_mismatches: list[str] = []

        def _check_url(image: Image) -> tuple[bool, str | None]:
            url = image.image_url
            if not url:
                return False, "missing image_url"
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return False, f"unsupported scheme {parsed.scheme!r}"

            file_slug = Path(parsed.path).stem.lower()
            if file_slug and file_slug != (image.slug or "").lower():
                slug_mismatches.append(f"{image.slug} -> {file_slug}")

            # Issue HTTP request
            method = primary_method.lower()
            try:
                resp = requests.request(method, url, timeout=timeout, allow_redirects=True)
            except requests.RequestException as exc:
                return False, f"{exc.__class__.__name__}: {exc}"

            status = resp.status_code
            if status != 405 and status < 400:
                return True, None

            # Retry with GET if HEAD failed or 405/4xx
            if method != "get":
                try:
                    resp = requests.get(url, stream=True, timeout=timeout)
                    status = resp.status_code
                except requests.RequestException as exc:
                    return False, f"GET fallback failed: {exc}"

            if status >= 400:
                return False, f"HTTP {status}"
            return True, None

        iterator = qs.iterator(chunk_size=chunk_size)
        for image in iterator:
            checked += 1
            ok, error = _check_url(image)
            if not ok:
                msg = f"{image.slug} ({image.id}) -> {image.image_url}: {error}"
                http_failures.append(msg)
                self.stderr.write(self.style.ERROR(msg))
                if fail_fast:
                    break

            if checked % 200 == 0:
                percent = (checked / (limit or (total - offset)) * 100)
                self.stdout.write(f"Checked {checked} images ({percent:.1f}% of target)")

        self.stdout.write(self.style.SUCCESS(f"Verification finished. Checked {checked} images."))
        self.stdout.write(f"  HTTP failures : {len(http_failures)}")
        self.stdout.write(f"  Slug mismatch : {len(slug_mismatches)}")

        if http_failures:
            self.stdout.write("First failures:")
            for line in http_failures[:10]:
                self.stdout.write(f"  - {line}")

        if slug_mismatches:
            self.stdout.write("Slug mismatches (image.slug -> filename slug):")
            for line in slug_mismatches[:10]:
                self.stdout.write(f"  - {line}")

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

import logging
import re

from apps.images.models import Image, Tag


logger = logging.getLogger(__name__)


TAG_PREFIX_PATTERN = re.compile(r"\b[Tt]ags\s*:\s*(?P<tags>[^|\n\r]*)")
ACTORS_PREFIX_PATTERN = re.compile(r"\b[Aa]ctors?\s*:\s*(?P<actors>[^|\n\r]*)")


def parse_csv_values(block: str):
    if not block:
        return []
    # Split by comma and pipe-safe trim
    parts = [p.strip() for p in block.split(',')]
    # Filter out empties and overly long noise
    return [p for p in parts if p]


class Command(BaseCommand):
    help = "Normalize image descriptions: move 'Tags:' values to Image.tags and remove tag/actor prefixes from description."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000)
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--start-id', type=int, default=None, help='Start from Image.id >= start-id')
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        start_id = options['start_id']
        dry_run = options['dry_run']

        qs = Image.objects.all().order_by('id')
        if start_id is not None:
            qs = qs.filter(id__gte=start_id)

        # Only images that potentially contain prefixes (use icontains for portability)
        from django.db.models import Q
        qs = qs.filter(
            Q(description__icontains='Tags:') |
            Q(description__icontains='tags:') |
            Q(description__icontains='Actors:') |
            Q(description__icontains='actors:')
        )

        total = qs.count()
        if limit is not None:
            # Evaluate ids to avoid slicing queryset many times later
            ids = list(qs.values_list('id', flat=True)[:limit])
            qs = Image.objects.filter(id__in=ids).order_by('id')
            total = len(ids)

        self.stdout.write(self.style.MIGRATE_HEADING('Normalize Image Tags'))
        self.stdout.write(f"Targets: {total} images | batch_size={batch_size} | dry_run={dry_run}")

        processed = 0
        updated = 0
        created_tags = 0

        def ensure_tag(name: str):
            nonlocal created_tags
            # Normalize whitespace; keep case as-is for display
            clean = ' '.join(name.split())
            if not clean:
                return None
            slug = slugify(clean)
            if not slug:
                return None
            tag, created = Tag.objects.get_or_create(slug=slug, defaults={'name': clean})
            if created:
                created_tags += 1
            return tag

        # Process in batches
        while True:
            batch = list(qs.values_list('id', flat=True)[processed:processed + batch_size])
            if not batch:
                break

            images = list(Image.objects.filter(id__in=batch).order_by('id').prefetch_related('tags'))

            with transaction.atomic():
                for image in images:
                    original_desc = image.description or ''
                    if not original_desc:
                        processed += 1
                        continue

                    # Extract tag and actor blocks
                    tag_block_match = TAG_PREFIX_PATTERN.search(original_desc)
                    actor_block_match = ACTORS_PREFIX_PATTERN.search(original_desc)

                    tags_added = 0
                    new_desc = original_desc

                    if tag_block_match:
                        tag_block = tag_block_match.group('tags') or ''
                        tag_names = parse_csv_values(tag_block)
                        tag_objs = []
                        for name in tag_names:
                            tag_obj = ensure_tag(name)
                            if tag_obj is not None:
                                tag_objs.append(tag_obj)
                        if tag_objs and not dry_run:
                            # Add without removing existing tags
                            image.tags.add(*tag_objs)
                            tags_added += len(tag_objs)
                        # Remove the 'Tags: ...' segment from description
                        new_desc = TAG_PREFIX_PATTERN.sub('', new_desc).strip()

                    # Remove the 'Actors: ...' segment from description as requested
                    if actor_block_match:
                        new_desc = ACTORS_PREFIX_PATTERN.sub('', new_desc).strip()

                    # Also remove redundant separators like leading/trailing pipes and extra spaces
                    new_desc = re.sub(r"\s*\|\s*", ' | ', new_desc)
                    new_desc = new_desc.strip(' |\t\r\n')

                    if new_desc != original_desc and not dry_run:
                        image.description = new_desc if new_desc else None
                        image.save(update_fields=['description'])
                        updated += 1

                    processed += 1

            self.stdout.write(f"Processed: {processed}/{total} | updated_descriptions={updated} | new_tags={created_tags}")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed={processed}, updated_descriptions={updated}, new_tags_created={created_tags}"))



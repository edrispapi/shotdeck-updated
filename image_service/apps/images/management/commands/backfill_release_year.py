from django.core.management.base import BaseCommand
from django.db import transaction

from apps.images.models import Image


class Command(BaseCommand):
    help = "Backfill Image.release_year from linked YearOption.value where available, then from Movie.year"

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=2000)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # Phase 1: from YearOption
        qs = Image.objects.filter(release_year__isnull=True, year__isnull=False).select_related('year').order_by('id')
        total = qs.count()
        self.stdout.write(f"Backfilling release_year from YearOption: targets={total}, batch_size={batch_size}, dry_run={dry_run}")

        processed = 0
        updated = 0
        while processed < total:
            ids = list(qs.values_list('id', flat=True)[processed: processed + batch_size])
            if not ids:
                break
            images = list(Image.objects.filter(id__in=ids).select_related('year').order_by('id'))
            with transaction.atomic():
                for img in images:
                    try:
                        if img.year and img.year.value and str(img.year.value).isdigit():
                            if not dry_run:
                                img.release_year = int(img.year.value)
                                img.save(update_fields=['release_year'])
                            updated += 1
                    except Exception:
                        pass
            processed += len(images)
            self.stdout.write(f"Processed {processed}/{total} (updated={updated})")

        # Phase 2: from Movie.year
        qs2 = Image.objects.filter(release_year__isnull=True, movie__isnull=False).select_related('movie').order_by('id')
        total2 = qs2.count()
        self.stdout.write(f"Backfilling release_year from Movie.year: targets={total2}")
        processed2 = 0
        updated2 = 0
        while processed2 < total2:
            ids2 = list(qs2.values_list('id', flat=True)[processed2: processed2 + batch_size])
            if not ids2:
                break
            images2 = list(Image.objects.filter(id__in=ids2).select_related('movie').order_by('id'))
            with transaction.atomic():
                for img in images2:
                    try:
                        if img.movie and img.movie.year:
                            if not dry_run:
                                img.release_year = img.movie.year
                                img.save(update_fields=['release_year'])
                            updated2 += 1
                    except Exception:
                        pass
            processed2 += len(images2)
            self.stdout.write(f"Processed {processed2}/{total2} (updated={updated2})")

        remaining = Image.objects.filter(release_year__isnull=True).count()
        self.stdout.write(self.style.SUCCESS(f"Done. updated_from_year={updated}, updated_from_movie={updated2}, remaining without release_year: {remaining}"))



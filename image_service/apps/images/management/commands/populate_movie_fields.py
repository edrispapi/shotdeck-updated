from django.core.management.base import BaseCommand
from django.db import transaction
from collections import Counter

from apps.images.models import Image, Movie


class Command(BaseCommand):
    help = "Populate Movie.crew fields (director/cinematographer/editor) and image_count from linked images"

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=500)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        movie_ids = list(Movie.objects.values_list('id', flat=True).order_by('id'))
        total = len(movie_ids)
        self.stdout.write(f"Populate movies: targets={total}, batch_size={batch_size}, dry_run={dry_run}")

        processed = 0
        updated = 0
        while processed < total:
            chunk = movie_ids[processed: processed + batch_size]
            if not chunk:
                break
            movies = list(Movie.objects.filter(id__in=chunk).order_by('id'))
            with transaction.atomic():
                for mv in movies:
                    images = list(Image.objects.filter(movie=mv).select_related('director', 'cinematographer', 'editor'))
                    if not images:
                        # still update image_count to 0 if different
                        if mv.image_count != 0 and not dry_run:
                            mv.image_count = 0
                            mv.save(update_fields=['image_count'])
                            updated += 1
                        continue

                    # Majority vote per field among images
                    def pick_majority(getter):
                        vals = [getter(img) for img in images if getter(img) is not None]
                        if not vals:
                            return None
                        c = Counter(vals)
                        return c.most_common(1)[0][0]

                    majority_director = pick_majority(lambda i: i.director)
                    majority_cine = pick_majority(lambda i: i.cinematographer)
                    majority_editor = pick_majority(lambda i: i.editor)

                    changed = False
                    if majority_director and mv.director_id != majority_director.id:
                        mv.director = majority_director
                        changed = True
                    if majority_cine and mv.cinematographer_id != majority_cine.id:
                        mv.cinematographer = majority_cine
                        changed = True
                    if majority_editor and mv.editor_id != majority_editor.id:
                        mv.editor = majority_editor
                        changed = True

                    # Update image_count
                    count = len(images)
                    if mv.image_count != count:
                        mv.image_count = count
                        changed = True

                    if changed and not dry_run:
                        mv.save(update_fields=['director', 'cinematographer', 'editor', 'image_count'])
                        updated += 1

            processed += len(movies)
            self.stdout.write(f"Processed {processed}/{total} (updated={updated})")

        self.stdout.write(self.style.SUCCESS(f"Done. updated_movies={updated}"))



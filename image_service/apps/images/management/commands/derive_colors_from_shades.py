from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.images.models import Image, ColorOption


def hex_to_rgb(hex_str: str):
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) != 6:
        return None
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b)
    except Exception:
        return None


def rgb_to_basic_color_name(rgb):
    if rgb is None:
        return None
    r, g, b = rgb

    # Simple heuristic mapping based on dominant channel and thresholds.
    channels = {'red': r, 'green': g, 'blue': b}
    dominant = max(channels, key=channels.get)
    max_v = channels[dominant]
    min_v = min(r, g, b)

    # Grayscale-ish -> map to 'gray'
    if abs(r - g) < 30 and abs(g - b) < 30:
        # brightness buckets for black/white/gray
        if max_v < 60:
            return 'black'
        if max_v > 200:
            return 'white'
        return 'gray'

    # Color detection with better thresholds
    if dominant == 'red':
        if g > 100 and r > 100 and b < 80:
            return 'yellow'
        if b > 100 and r > 100 and g < 80:
            return 'magenta'
        if r > 120:
            return 'red'
    elif dominant == 'green':
        if b > 100 and g > 100 and r < 80:
            return 'cyan'
        if g > 120:
            return 'green'
    elif dominant == 'blue':
        if b > 120:
            return 'blue'
    
    # Fallback to gray for low-intensity colors
    if max_v < 80:
        return 'black'
    elif max_v > 180:
        return 'white'
    else:
        return 'gray'


class Command(BaseCommand):
    help = "Derive Image.color from primary_color_hex, shade hex, or dominant_colors; create ColorOption values if needed."

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=2000)
        parser.add_argument('--dry-run', action='store_true', default=False)

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        qs = Image.objects.filter(color__isnull=True).select_related('shade').order_by('id')
        total = qs.count()
        self.stdout.write(f"Deriving colors: targets={total}, batch_size={batch_size}, dry_run={dry_run}")

        processed = 0
        updated = 0
        created_options = 0

        def get_color_option(name: str):
            nonlocal created_options
            slug = slugify(name)
            opt, created = ColorOption.objects.get_or_create(value=name, defaults={'slug': slug})
            if created:
                created_options += 1
            return opt

        while processed < total:
            ids = list(qs.values_list('id', flat=True)[processed: processed + batch_size])
            if not ids:
                break
            images = list(Image.objects.filter(id__in=ids).select_related('shade').order_by('id'))
            with transaction.atomic():
                for img in images:
                    try:
                        hex_value = None
                        # Priority 1: primary_color_hex
                        if getattr(img, 'primary_color_hex', None):
                            hex_value = str(img.primary_color_hex).strip()
                        # Priority 2: shade option
                        if not hex_value and img.shade and img.shade.value:
                            hex_value = str(img.shade.value).strip()
                        # Priority 3: dominant_colors list (pick first)
                        if not hex_value and getattr(img, 'dominant_colors', None):
                            try:
                                if isinstance(img.dominant_colors, (list, tuple)) and img.dominant_colors:
                                    hex_value = str(img.dominant_colors[0]).strip()
                            except Exception:
                                pass

                        rgb = hex_to_rgb(hex_value or '')
                        color_name = rgb_to_basic_color_name(rgb)
                        if not color_name:
                            continue
                        if not dry_run:
                            img.color = get_color_option(color_name)
                            img.save(update_fields=['color'])
                        updated += 1
                    except Exception:
                        pass
            processed += len(images)
            self.stdout.write(f"Processed {processed}/{total} (updated={updated}, new_color_options={created_options})")

        self.stdout.write(self.style.SUCCESS(f"Done. updated={updated}, created_color_options={created_options}"))



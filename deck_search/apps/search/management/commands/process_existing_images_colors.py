from django.core.management.base import BaseCommand
from apps.images.models import Image
from apps.search.documents import ImageDocument
from apps.color_ai.color_processor import UltimateColorProcessor
import logging
from pathlib import Path
import requests
from io import BytesIO
from PIL import Image as PILImage
import tempfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process existing images with UltimateColorProcessor and index in Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, help='Limit number of images')
        parser.add_argument('--batch-size', type=int, default=50)
        parser.add_argument('--skip-existing', action='store_true', 
                          help='Skip images that already have color data')

    def handle(self, *args, **options):
        limit = options.get('limit')
        batch_size = options.get('batch_size', 50)
        skip_existing = options.get('skip_existing', False)

        try:
            ImageDocument.init()
            self.stdout.write(self.style.SUCCESS('✅ Elasticsearch initialized'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed: {e}'))
            return

        # Get images
        images = Image.objects.all()
        
        if skip_existing:
            # Only process images without color data
            images = images.filter(primary_color_hex__isnull=True) | images.filter(primary_color_hex='')
            self.stdout.write(f'�� Found {images.count()} images without color data')
        
        if limit:
            images = images[:limit]

        total = images.count()
        self.stdout.write(f'🎨 Processing {total} images with UltimateColorProcessor')

        # Initialize color processor
        temp_dir = tempfile.mkdtemp()
        processor = UltimateColorProcessor(images_folder=temp_dir, max_colors=15)

        processed = 0
        failed = 0
        skipped = 0

        for image in images:
            try:
                # Download image to temp file
                temp_image_path = self.download_image(image.image_url, temp_dir)
                
                if not temp_image_path:
                    skipped += 1
                    continue

                # Process with UltimateColorProcessor
                analysis_result = processor.analyze_image_colors(temp_image_path)
                
                if not analysis_result or not analysis_result.get('main_palette'):
                    skipped += 1
                    self.stdout.write(f'⚠️  No colors extracted for {image.slug}')
                    continue

                # Convert to database format
                color_data = self.convert_analysis_to_db_format(analysis_result)

                # Update database (if you want to save to DB)
                # self.update_image_color_data(image, color_data)

                # Index in Elasticsearch
                self.index_image_with_colors(image, color_data)

                processed += 1

                if processed % 10 == 0:
                    self.stdout.write(f'⏳ Processed {processed}/{total}')

                # Clean up temp file
                temp_image_path.unlink(missing_ok=True)

            except Exception as e:
                failed += 1
                logger.error(f'Failed processing {image.id}: {e}')
                self.stdout.write(self.style.WARNING(f'❌ Failed: {image.slug} - {str(e)[:50]}'))

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        self.stdout.write(self.style.SUCCESS(f'✅ Processed: {processed}/{total}'))
        self.stdout.write(self.style.WARNING(f'⚠️  Skipped: {skipped}, Failed: {failed}'))

    def download_image(self, image_url, temp_dir):
        """Download image from URL to temp file"""
        if not image_url:
            return None

        try:
            # Handle different URL formats
            if image_url.startswith('/media/'):
                full_url = f"http://image_service:8000{image_url}"
            elif image_url.startswith('http'):
                full_url = image_url
            else:
                return None

            # Download
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()

            # Save to temp file
            img = PILImage.open(BytesIO(response.content))
            temp_path = Path(temp_dir) / f"temp_{hash(image_url)}.jpg"
            img.save(temp_path, 'JPEG')

            return temp_path

        except Exception as e:
            logger.error(f'Failed to download {image_url}: {e}')
            return None

    def convert_analysis_to_db_format(self, analysis_result):
        """Convert UltimateColorProcessor output to database format"""
        main_palette = analysis_result.get('main_palette', [])
        analogous_palette = analysis_result.get('analogous_palette', [])

        # Extract dominant colors
        dominant_colors = [
            {
                'hex': color['hex'],
                'rgb': list(color['rgb']),
                'percentage': color.get('count', 0),
                'hsl': {
                    'hue': color.get('hue', 0),
                    'saturation': color.get('saturation', 0),
                    'lightness': color.get('lightness', 0)
                }
            }
            for color in main_palette[:10]
        ]

        # Primary colors (top 5)
        primary_colors = [
            {
                'rank': i + 1,
                'hex': color['hex'],
                'rgb': list(color['rgb']),
                'percentage': color.get('count', 0),
                'hsl': {
                    'hue': color.get('hue', 0),
                    'saturation': color.get('saturation', 0),
                    'lightness': color.get('lightness', 0)
                },
                'is_main': i == 0
            }
            for i, color in enumerate(main_palette[:5])
        ]

        # Primary color hex
        primary_color_hex = main_palette[0]['hex'] if main_palette else ''

        # Color samples (from analogous palette)
        color_samples = [
            {
                'hex': color['hex'],
                'rgb': list(color['rgb'])
            }
            for color in analogous_palette[:10]
        ]

        # Color search terms
        color_search_terms = []
        for color in main_palette[:5]:
            hex_color = color['hex'].lower()
            color_search_terms.append(hex_color)
            
            # Add color name based on hue
            hue = color.get('hue', 0)
            color_name = self.get_color_name_from_hue(hue)
            color_search_terms.append(color_name)

        # Determine color temperature
        if main_palette:
            avg_hue = sum(c.get('hue', 0) for c in main_palette[:3]) / min(3, len(main_palette))
            if 0 <= avg_hue < 60 or avg_hue >= 300:
                color_temperature = 'warm'
            elif 180 <= avg_hue < 300:
                color_temperature = 'cool'
            else:
                color_temperature = 'neutral'
        else:
            color_temperature = 'neutral'

        return {
            'dominant_colors': dominant_colors,
            'primary_colors': primary_colors,
            'primary_color_hex': primary_color_hex,
            'color_palette': {
                'main': main_palette,
                'analogous': analogous_palette[:25]
            },
            'color_samples': color_samples,
            'color_temperature': color_temperature,
            'color_search_terms': list(set(color_search_terms)),
            'hue_range': f"{int(main_palette[0].get('hue', 0)) - 30}-{int(main_palette[0].get('hue', 0)) + 30}" if main_palette else "0-360"
        }

    def get_color_name_from_hue(self, hue):
        """Get color name from hue value"""
        if hue < 30 or hue >= 330:
            return 'red'
        elif 30 <= hue < 60:
            return 'orange'
        elif 60 <= hue < 90:
            return 'yellow'
        elif 90 <= hue < 150:
            return 'green'
        elif 150 <= hue < 210:
            return 'cyan'
        elif 210 <= hue < 270:
            return 'blue'
        elif 270 <= hue < 330:
            return 'purple'
        else:
            return 'neutral'

    def update_image_color_data(self, image, color_data):
        """Update image model with color data (optional - if you want to save to DB)"""
        try:
            image.dominant_colors = color_data['dominant_colors']
            image.primary_colors = color_data['primary_colors']
            image.primary_color_hex = color_data['primary_color_hex']
            image.color_palette = color_data['color_palette']
            image.color_samples = color_data['color_samples']
            image.color_temperature = color_data['color_temperature']
            image.color_search_terms = color_data['color_search_terms']
            image.hue_range = color_data['hue_range']
            image.save()
            logger.info(f'Updated DB for image {image.id}')
        except Exception as e:
            logger.error(f'Failed to update DB for image {image.id}: {e}')

    def index_image_with_colors(self, image, color_data):
        """Index image in Elasticsearch with color data"""
        def get_option_value(obj):
            return obj.value if obj and hasattr(obj, 'value') else None

        doc_data = {
            'id': image.id,
            'slug': image.slug,
            'title': image.title or '',
            'description': image.description or '',
            'image_url': image.image_url or '',
            'release_year': image.release_year,
            'created_at': image.created_at,
            'updated_at': image.updated_at,
            
            # Options
            'media_type': get_option_value(image.media_type),
            'color': get_option_value(image.color),
            'genre': [g.value for g in image.genre.all()],
            
            # Color data from processor
            'dominant_colors': color_data['dominant_colors'],
            'primary_colors': color_data['primary_colors'],
            'primary_color_hex': color_data['primary_color_hex'],
            'color_palette': color_data['color_palette'],
            'color_samples': color_data['color_samples'],
            'color_temperature': color_data['color_temperature'],
            'color_search_terms': color_data['color_search_terms'],
            'hue_range': color_data['hue_range'],
        }

        # Movie & Tags
        if image.movie:
            doc_data['movie'] = {
                'id': image.movie.id,
                'slug': image.movie.slug,
                'title': image.movie.title,
                'year': image.movie.year,
            }

        doc_data['tags'] = [
            {'id': tag.id, 'slug': tag.slug, 'name': tag.name}
            for tag in image.tags.all()
        ]

        # Index
        doc = ImageDocument(meta={'id': image.id}, **doc_data)
        doc.save()

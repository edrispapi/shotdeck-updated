# /home/a/shotdeck-main/deck_search/apps/color_ai/management/commands/analyze_from_service.py

from django.core.management.base import BaseCommand
from django.conf import settings
import sys
import os
import json
import logging

# Add the project root to path
sys.path.insert(0, '/home/a/shotdeck-main/deck_search')

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Download and analyze images from the image service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of images to analyze'
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Pagination offset'
        )
        parser.add_argument(
            '--movie',
            type=str,
            help='Filter by movie slug'
        )
        parser.add_argument(
            '--director',
            type=str,
            help='Filter by director'
        )
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://localhost:8000/api',
            help='Image service API URL'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Save results to JSON file'
        )
        parser.add_argument(
            '--uuid',
            type=str,
            help='Analyze single image by UUID'
        )

    def handle(self, *args, **options):
        try:
            from apps.color_ai.image_service_client import ImageServiceClient
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "Error: Cannot import ImageServiceClient. "
                    "Make sure color_ai app is properly configured."
                )
            )
            return

        client = ImageServiceClient(api_base_url=options['api_url'])
        
        # Single image mode
        if options['uuid']:
            self._analyze_single(client, options)
            return
        
        # Batch mode
        self._analyze_batch(client, options)

    def _analyze_single(self, client, options):
        """Analyze a single image by UUID"""
        uuid = options['uuid']
        self.stdout.write(f"Analyzing single image: {uuid}")
        
        result = client.sync_and_update(uuid)
        
        if result.get('error'):
            self.stdout.write(self.style.ERROR(f"Error: {result['error']}"))
            return
        
        analysis = result.get('color_analysis', {})
        
        if analysis.get('success'):
            self.stdout.write(self.style.SUCCESS("\n✅ Analysis successful!"))
            
            # Display results
            title = result.get('title', 'Unknown')
            self.stdout.write(f"\nImage: {title}")
            
            main_palette = analysis.get('main_palette', [])
            self.stdout.write(f"\nMain Palette ({len(main_palette)} colors):")
            
            for i, color in enumerate(main_palette[:10], 1):
                self.stdout.write(
                    f"  {i:2d}. {color['hex']} - "
                    f"H:{color['hue']:6.1f}° "
                    f"S:{color['saturation']:5.1f}% "
                    f"L:{color['lightness']:5.1f}%"
                )
            
            analogous = analysis.get('analogous_palette', [])
            if analogous:
                self.stdout.write(f"\nAnalogous Palette: {len(analogous)} colors")
        else:
            self.stdout.write(
                self.style.ERROR(f"Analysis failed: {analysis.get('error')}")
            )
        
        # Save to file if requested
        if options['output']:
            self._save_to_file(result, options['output'])

    def _analyze_batch(self, client, options):
        """Analyze multiple images"""
        filters = {}
        if options['movie']:
            filters['movie'] = options['movie']
        if options['director']:
            filters['director'] = options['director']
        
        self.stdout.write("=" * 70)
        self.stdout.write(
            f"Fetching and analyzing {options['limit']} images "
            f"(offset: {options['offset']})"
        )
        if filters:
            self.stdout.write(f"Filters: {filters}")
        self.stdout.write("=" * 70)
        
        results = client.batch_analyze(
            limit=options['limit'],
            offset=options['offset'],
            **filters
        )
        
        if not results:
            self.stdout.write(self.style.WARNING("\nNo images found!"))
            return
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"Analyzed {len(results)} images:\n")
        
        successful = 0
        failed = 0
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Unknown')[:50]
            analysis = result.get('color_analysis', {})
            
            if analysis.get('success'):
                successful += 1
                main_palette = analysis.get('main_palette', [])
                primary = main_palette[0] if main_palette else None
                
                if primary:
                    self.stdout.write(
                        f"  ✅ {i:2d}. {title}\n"
                        f"       Primary: {primary['hex']} | "
                        f"Total colors: {len(main_palette)} | "
                        f"Analogous: {len(analysis.get('analogous_palette', []))}"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  {i:2d}. {title} - No colors extracted"
                        )
                    )
            else:
                failed += 1
                error = analysis.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {i:2d}. {title} - {error}")
                )
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Complete! {successful} successful, {failed} failed"
            )
        )
        
        # Save results if output specified
        if options['output']:
            self._save_to_file(results, options['output'])

    def _save_to_file(self, data, filename):
        """Save results to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.stdout.write(
                self.style.SUCCESS(f"\n📁 Results saved to: {filename}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Failed to save file: {e}")
            )
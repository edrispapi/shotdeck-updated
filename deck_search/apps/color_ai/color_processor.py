# /home/a/shotdeck-main/deck_search/apps/color_ai/color_processor.py

#!/usr/bin/env python3
"""
Advanced Color Analyzer - Maximum Diversity Palette Extraction
Features: High-diversity sampling, detailed analogous harmony suggestions, subject-aware analysis,
and integration with image service for automatic downloading and processing.
"""

import os
import sys
import time
import logging
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple
from io import BytesIO
import colorsys
import numpy as np
from PIL import Image
from collections import Counter

# Attempt to import face_recognition
try:
    import face_recognition  # type: ignore
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("WARNING: 'face_recognition' library not found. Subject detection will be disabled.")
    print("To enable this feature, please install it by running: pip install face-recognition opencv-python")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UltimateColorProcessor:
    """
    Advanced color analyzer for generating high-diversity palettes from local or remote images.
    Supports downloading from image service and caching for performance.
    """

    def __init__(
        self,
        images_folder: str = "/home/a/shotdeck-main/deck_search/images",
        cache_folder: str = "/home/a/shotdeck-main/deck_search/cache",
        max_colors: int = 15
    ):
        self.images_folder = Path(images_folder)
        self.cache_folder = Path(cache_folder)
        self.max_colors = max_colors
        self.image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        
        # Create folders if they don't exist
        self.images_folder.mkdir(exist_ok=True, parents=True)
        self.cache_folder.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"ColorProcessor initialized:")
        logger.info(f"  Images folder: {self.images_folder}")
        logger.info(f"  Cache folder: {self.cache_folder}")
        logger.info(f"  Max colors: {self.max_colors}")

    def download_image(self, image_url: str, image_id: str, force: bool = False) -> Optional[Path]:
        """
        Download image from URL and cache it locally.
        
        Args:
            image_url: URL of the image to download
            image_id: Unique identifier for the image
            force: Force re-download even if cached
            
        Returns:
            Path to cached image or None if failed
        """
        try:
            # Generate cache filename from image_id
            url_hash = hashlib.md5(f"{image_id}_{image_url}".encode()).hexdigest()
            cache_filename = f"{image_id}_{url_hash[:8]}.jpg"
            cache_path = self.cache_folder / cache_filename
            
            # Check if already cached
            if not force and cache_path.exists():
                logger.info(f"Using cached image: {cache_filename}")
                return cache_path
            
            # Download image
            logger.info(f"Downloading image from: {image_url}")
            response = requests.get(
                image_url,
                timeout=30,
                headers={'User-Agent': 'ShotDeck-ColorAnalyzer/2.0'},
                stream=True
            )
            response.raise_for_status()
            
            # Open and convert image
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save to cache
            image.save(cache_path, 'JPEG', quality=95)
            logger.info(f"Image cached: {cache_filename}")
            
            return cache_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing image from {image_url}: {e}")
            return None

    def analyze_from_url(self, image_url: str, image_id: str, force_download: bool = False) -> Dict:
        """
        Analyze image directly from URL (downloads and caches).
        
        Args:
            image_url: URL of the image
            image_id: Unique identifier for the image
            force_download: Force re-download
            
        Returns:
            Complete color analysis
        """
        cache_path = self.download_image(image_url, image_id, force=force_download)
        
        if cache_path is None:
            return {
                'error': True,
                'message': 'Failed to download image',
                'image_url': image_url,
                'image_id': image_id
            }
        
        return self.analyze_image_colors(cache_path)

    def _hls_to_hex(self, h, l, s) -> str:
        """Converts HLS color tuple (0-1 scale) to a HEX string."""
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
    
    def _get_color_properties(self, rgb) -> Dict:
        """Calculates all properties for a given RGB color."""
        r, g, b = rgb
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        return {
            'hex': "#{:02x}{:02x}{:02x}".format(r, g, b),
            'rgb': (r, g, b),
            'hsl': (h, l, s),
            'hue': h * 360,
            'saturation': s * 100,
            'lightness': l * 100
        }

    def _get_color_family(self, hue: float) -> str:
        """Helper method to determine color family from hue."""
        if hue < 30 or hue >= 330:
            return 'red'
        elif 30 <= hue < 60:
            return 'orange'
        elif 60 <= hue < 90:
            return 'yellow'
        elif 90 <= hue < 150:
            return 'green'
        elif 150 <= hue < 180:
            return 'cyan'
        elif 180 <= hue < 240:
            return 'blue'
        elif 240 <= hue < 300:
            return 'purple'
        else:
            return 'magenta'

    def generate_detailed_analogous_palette(self, main_palette: List[Dict]) -> List[Dict]:
        """Generates analogous color harmony based on color families present in main palette."""
        if not main_palette:
            return []

        # Identify color families present in main palette
        color_families = {
            'red': [], 'orange': [], 'yellow': [], 'green': [],
            'cyan': [], 'blue': [], 'purple': [], 'magenta': []
        }

        for color in main_palette:
            if 'hue' in color:
                hue = color['hue']
                family = self._get_color_family(hue)
                color_families[family].append(color)

        # Find active color families
        active_families = {family: colors for family, colors in color_families.items() if colors}

        palette = []
        palette.extend(main_palette)

        # Generate analogous colors within active families
        for family_name, family_colors in active_families.items():
            # Calculate average properties
            total_h, total_s, total_l = 0, 0, 0
            for color in family_colors:
                if 'hsl' in color:
                    h, l, s = color['hsl']
                    total_h += h
                    total_s += s
                    total_l += l

            avg_h = total_h / len(family_colors)
            avg_s = total_s / len(family_colors)
            avg_l = total_l / len(family_colors)

            # Define hue range for this family
            hue_ranges = {
                'red': (-30, 30), 'orange': (10, 50), 'yellow': (40, 80),
                'green': (80, 160), 'cyan': (140, 200), 'blue': (180, 270),
                'purple': (240, 300), 'magenta': (280, 340)
            }
            hue_range = hue_ranges.get(family_name, (0, 360))

            # Generate variations
            saturation_variations = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            lightness_variations = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

            for sat_var in saturation_variations:
                for light_var in lightness_variations:
                    for hue_offset in [-20, -10, 0, 10, 20]:
                        new_h = (avg_h + hue_offset / 360) % 1.0

                        # Ensure hue stays within family range
                        hue_degrees = new_h * 360
                        if hue_degrees < hue_range[0]:
                            hue_degrees = hue_range[0]
                        elif hue_degrees > hue_range[1]:
                            hue_degrees = hue_range[1]
                        new_h = hue_degrees / 360

                        new_s = max(0.1, min(1.0, avg_s * sat_var))
                        new_l = max(0.15, min(0.95, avg_l * light_var))

                        rgb_float = colorsys.hls_to_rgb(new_h, new_l, new_s)
                        rgb_int = tuple(int(c * 255) for c in rgb_float)

                        palette.append(self._get_color_properties(rgb_int))

        # Remove duplicates
        unique_palette = list({p['hex']: p for p in palette}.values())
        unique_palette.sort(key=lambda c: c['lightness'])

        # Select diverse colors
        if len(unique_palette) > 25:
            selected = []
            selected.extend(main_palette)

            remaining = [c for c in unique_palette if c not in main_palette]
            family_groups = {}

            for color in remaining:
                hue = color.get('hue', 0)
                family = self._get_color_family(hue)
                if family not in family_groups:
                    family_groups[family] = []
                family_groups[family].append(color)

            active_families_count = len(active_families)
            remaining_slots = 25 - len(main_palette)
            slots_per_family = max(1, remaining_slots // active_families_count) if active_families_count > 0 else 1

            for family_name, colors in family_groups.items():
                if colors:
                    colors.sort(key=lambda c: c.get('lightness', 0) + c.get('saturation', 0), reverse=True)
                    take_count = min(len(colors), slots_per_family)
                    selected.extend(colors[:take_count])

            return selected[:25]

        return unique_palette[:25]

    def extract_colors_max_diversity(self, image_path: Path, max_colors: int = 15) -> List[Dict]:
        """
        Extracts a palette with maximum diversity by sampling from different regions and brightness levels.
        """
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                img_array = np.array(img)
                height, width, _ = img_array.shape
                
                candidate_pixels = []
                
                # Enhanced grid sampling
                for scale in [50, 75, 100]:
                    step = max(1, min(width, height) // scale)
                    grid_pixels = img_array[::step, ::step, :].reshape(-1, 3)
                    candidate_pixels.extend([tuple(p) for p in grid_pixels])

                # Random sampling with brightness stratification
                num_random_samples = min(4000, width * height // 16)
                random_indices_y = np.random.randint(0, height, num_random_samples)
                random_indices_x = np.random.randint(0, width, num_random_samples)
                random_pixels = img_array[random_indices_y, random_indices_x]
                candidate_pixels.extend([tuple(p) for p in random_pixels])

                # Edge sampling
                edge_width = max(1, min(width, height) // 30)
                
                # Top edge
                top_pixels = img_array[:edge_width, :, :].reshape(-1, 3)
                candidate_pixels.extend([tuple(p) for p in top_pixels[::max(1, len(top_pixels)//200)]])

                # Bottom edge
                bottom_pixels = img_array[-edge_width:, :, :].reshape(-1, 3)
                candidate_pixels.extend([tuple(p) for p in bottom_pixels[::max(1, len(bottom_pixels)//200)]])

                # Left and right edges
                left_pixels = img_array[:, :edge_width, :].reshape(-1, 3)
                candidate_pixels.extend([tuple(p) for p in left_pixels[::max(1, len(left_pixels)//200)]])

                right_pixels = img_array[:, -edge_width:, :].reshape(-1, 3)
                candidate_pixels.extend([tuple(p) for p in right_pixels[::max(1, len(right_pixels)//200)]])

                # Remove duplicates
                unique_pixels = list(set(candidate_pixels))
                
                if not unique_pixels:
                    return []

                # Select diverse colors
                selected_colors = []
                
                pixel_counts = Counter(candidate_pixels)
                candidates = pixel_counts.most_common(10)
                best_candidate = None
                best_score = -1

                for pixel, count in candidates:
                    r, g, b = pixel
                    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
                    lightness_score = 1.0 - abs(l - 0.35)
                    saturation_score = min(s * 1.5, 1.0)
                    frequency_score = count / len(candidate_pixels)
                    total_score = lightness_score * 0.4 + saturation_score * 0.3 + frequency_score * 0.3

                    if total_score > best_score:
                        best_score = total_score
                        best_candidate = pixel

                first_pixel = best_candidate if best_candidate else pixel_counts.most_common(1)[0][0]
                selected_colors.append(self._get_color_properties(first_pixel))
                
                # Convert to HSL
                unique_pixels_hsl = {p: colorsys.rgb_to_hls(p[0]/255, p[1]/255, p[2]/255) for p in unique_pixels}

                while len(selected_colors) < max_colors and len(unique_pixels) > len(selected_colors):
                    best_candidate = None
                    max_score = -1

                    for pixel, hsl in unique_pixels_hsl.items():
                        if pixel in [tuple(c['rgb']) for c in selected_colors]:
                            continue

                        h, l, s = hsl
                        lightness_score = 1.0 - abs(l - 0.4) * 1.5
                        saturation_score = min(s * 1.8, 1.0)

                        min_dist_to_selected = float('inf')
                        for sel_color in selected_colors:
                            sel_hsl = sel_color['hsl']
                            hue_diff = abs(h - sel_hsl[0])
                            hue_dist = min(hue_diff, 1.0 - hue_diff) * 3
                            light_dist = abs(l - sel_hsl[1]) * 2
                            sat_dist = abs(s - sel_hsl[2]) * 1
                            total_dist = hue_dist + light_dist + sat_dist

                            if total_dist < min_dist_to_selected:
                                min_dist_to_selected = total_dist

                        diversity_score = min_dist_to_selected / 6.0
                        quality_score = (lightness_score + saturation_score) / 2.0
                        total_score = diversity_score * 0.7 + quality_score * 0.3

                        if total_score > max_score:
                            max_score = total_score
                            best_candidate = pixel
                    
                    if best_candidate:
                        selected_colors.append(self._get_color_properties(best_candidate))
                    else:
                        break

                # Add count information
                for color in selected_colors:
                    color['count'] = pixel_counts.get(color['rgb'], 1)
                
                # Sort by lightness
                selected_colors.sort(key=lambda c: c['lightness'])
                
                return selected_colors

        except Exception as e:
            logger.error(f"Error in max diversity extraction for {image_path}: {e}")
            return []

    def analyze_image_colors(self, image_path: Path) -> Dict:
        """
        Performs a full analysis on an image: main palette and analogous harmonies.
        """
        try:
            main_palette = self.extract_colors_max_diversity(image_path, max_colors=self.max_colors)
            
            analogous_palette = []
            if main_palette:
                analogous_palette = self.generate_detailed_analogous_palette(main_palette)
                
            return {
                'success': True,
                'image_path': str(image_path),
                'main_palette': main_palette,
                'analogous_palette': analogous_palette,
                'primary_color': main_palette[0] if main_palette else None,
                'color_count': len(main_palette),
                'metadata': {
                    'max_colors': self.max_colors,
                    'palette_size': len(main_palette),
                    'analogous_size': len(analogous_palette)
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }

    def analyze_all_images(self) -> Dict:
        """Analyzes all images in the images folder."""
        print("=" * 70)
        print("🎨 ADVANCED COLOR ANALYZER - Maximum Diversity Edition 🎨")
        print(f"🌈 {self.max_colors} High-Quality Colors | 25+ Diverse Analogous Suggestions")
        print("=" * 70)

        image_files = sorted([p for ext in self.image_extensions for p in self.images_folder.glob(ext)])
        if not image_files:
            print("❌ No images found!")
            return {'success': False, 'message': 'No images found'}

        results = []
        start_time = time.time()

        for i, image_file in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] Analyzing: {image_file.name}")
            result = self.analyze_image_colors(image_file)
            results.append(result)
            print(f"  ✅ Analysis completed for {image_file.name}")

        total_time = time.time() - start_time

        print(f"\n✅ Processing completed successfully! {len(results)} images analyzed.")
        
        return {
            'success': True,
            'results': results,
            'summary': {
                'total_images': len(results),
                'total_time': round(total_time, 2),
                'successful': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success'))
            }
        }

    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear cached images.
        
        Args:
            older_than_days: Only clear files older than this many days
            
        Returns:
            Number of files deleted
        """
        import time
        from datetime import datetime, timedelta
        
        if not self.cache_folder.exists():
            return 0
        
        cutoff_time = None
        if older_than_days:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            cutoff_time = cutoff_date.timestamp()
        
        deleted = 0
        for file_path in self.cache_folder.glob('*.jpg'):
            if cutoff_time is None or file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted += 1
        
        logger.info(f"Cleared {deleted} cached images")
        return deleted


def main():
    """Main function for command line usage."""
    images_folder = sys.argv[1] if len(sys.argv) > 1 else "/home/a/shotdeck-main/deck_search/images"
    if not Path(images_folder).exists():
        print(f"❌ Images folder not found: {images_folder}")
        return

    processor = UltimateColorProcessor(images_folder=images_folder, max_colors=15)
    processor.analyze_all_images()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Advanced Color Analyzer - Maximum Diversity Palette Extraction
Features: High-diversity sampling, detailed analogous harmony suggestions, and subject-aware analysis.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Union
import colorsys
import numpy as np
from PIL import Image

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
    Advanced color analyzer for generating high-diversity palettes from local images.
    """

    def __init__(self, images_folder: str = "C:/shotdeck-main/search_service/images", max_colors: int = 15):
        self.images_folder = Path(images_folder)
        self.max_colors = max_colors
        self.image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        self.images_folder.mkdir(exist_ok=True)

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
            'saturation': s,
            'lightness': l
        }

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
                if hue < 30 or hue >= 330:
                    color_families['red'].append(color)
                elif 30 <= hue < 60:
                    color_families['orange'].append(color)
                elif 60 <= hue < 90:
                    color_families['yellow'].append(color)
                elif 90 <= hue < 150:
                    color_families['green'].append(color)
                elif 150 <= hue < 180:
                    color_families['cyan'].append(color)
                elif 180 <= hue < 240:
                    color_families['blue'].append(color)
                elif 240 <= hue < 300:
                    color_families['purple'].append(color)
                else:
                    color_families['magenta'].append(color)

        # Find active color families (those with at least one color)
        active_families = {family: colors for family, colors in color_families.items() if colors}

        palette = []
        # Add all main palette colors first
        palette.extend(main_palette)

        # Generate analogous colors only within active families
        for family_name, family_colors in active_families.items():
            # Calculate average properties for this family
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
            if family_name == 'red':
                hue_range = (-30, 30)
            elif family_name == 'orange':
                hue_range = (10, 50)
            elif family_name == 'yellow':
                hue_range = (40, 80)
            elif family_name == 'green':
                hue_range = (80, 160)
            elif family_name == 'cyan':
                hue_range = (140, 200)
            elif family_name == 'blue':
                hue_range = (180, 270)
            elif family_name == 'purple':
                hue_range = (240, 300)
            else:  # magenta
                hue_range = (280, 340)

            # Generate variations within family range
            saturation_variations = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            lightness_variations = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

            for sat_var in saturation_variations:
                for light_var in lightness_variations:
                    # Generate multiple hue variations within family range
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

        # Sort by lightness for smooth transition
        unique_palette.sort(key=lambda c: c['lightness'])

        # Select diverse colors from each family
        if len(unique_palette) > 25:
            selected = []
            # Always include main palette colors
            selected.extend(main_palette)

            # Group remaining colors by family and select proportionally
            remaining = [c for c in unique_palette if c not in main_palette]
            family_groups = {}

            for color in remaining:
                hue = color.get('hue', 0)
                family = self._get_color_family(hue)
                if family not in family_groups:
                    family_groups[family] = []
                family_groups[family].append(color)

            # Distribute remaining slots among active families
            active_families_count = len(active_families)
            remaining_slots = 25 - len(main_palette)
            slots_per_family = max(1, remaining_slots // active_families_count)

            for family_name, colors in family_groups.items():
                if colors:
                    # Sort by quality (lightness + saturation)
                    colors.sort(key=lambda c: c.get('lightness', 0) + c.get('saturation', 0), reverse=True)
                    take_count = min(len(colors), slots_per_family)
                    selected.extend(colors[:take_count])

            return selected[:25]

        return unique_palette[:25]

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


    def extract_colors_max_diversity(self, image_path: Path, max_colors: int = 15) -> List[Dict]:
        """
        Extracts a palette with maximum diversity by sampling from different regions and brightness levels,
        then selecting colors based on their difference from already chosen colors.
        """
        try:
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                img_array = np.array(img)
                height, width, _ = img_array.shape
                
                # Step 1: Gather a large pool of candidate pixels from various sources
                candidate_pixels = []
                
                # Source A: Enhanced grid sampling with multiple scales
                for scale in [50, 75, 100]:
                    step = max(1, min(width, height) // scale)
                    grid_pixels = img_array[::step, ::step, :].reshape(-1, 3)
                    candidate_pixels.extend([tuple(p) for p in grid_pixels])

                # Source B: Enhanced random sampling with brightness stratification
                num_random_samples = min(4000, width * height // 16)
                random_indices_y = np.random.randint(0, height, num_random_samples)
                random_indices_x = np.random.randint(0, width, num_random_samples)
                random_pixels = img_array[random_indices_y, random_indices_x]
                candidate_pixels.extend([tuple(p) for p in random_pixels])

                # Source C: Optimized edge sampling for speed
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

                # Remove duplicate pixels to work with unique colors
                unique_pixels = list(set(candidate_pixels))
                
                if not unique_pixels:
                    return []

                # Step 2: Select the most diverse colors from the pool
                selected_colors = []
                
                # Start with the most frequent color (optimized)
                from collections import Counter
                pixel_counts = Counter(candidate_pixels)

                # Find the most frequent color with balanced lightness
                candidates = pixel_counts.most_common(10)  # Get top 10 most frequent
                best_candidate = None
                best_score = -1

                for pixel, count in candidates:
                    r, g, b = pixel
                    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
                    # Prefer colors with medium lightness and good saturation
                    lightness_score = 1.0 - abs(l - 0.35)  # Prefer slightly dark colors
                    saturation_score = min(s * 1.5, 1.0)
                    frequency_score = count / len(candidate_pixels)
                    total_score = lightness_score * 0.4 + saturation_score * 0.3 + frequency_score * 0.3

                    if total_score > best_score:
                        best_score = total_score
                        best_candidate = pixel

                first_pixel = best_candidate if best_candidate else pixel_counts.most_common(1)[0][0]
                selected_colors.append(self._get_color_properties(first_pixel))
                
                # Convert all unique pixels to HSL for distance calculation
                unique_pixels_hsl = {p: colorsys.rgb_to_hls(p[0]/255, p[1]/255, p[2]/255) for p in unique_pixels}

                while len(selected_colors) < max_colors and len(unique_pixels) > len(selected_colors):
                    best_candidate = None
                    max_score = -1

                    for pixel, hsl in unique_pixels_hsl.items():
                        if pixel in [tuple(c['rgb']) for c in selected_colors]:
                            continue

                        # Calculate comprehensive score for color selection
                        h, l, s = hsl

                        # Prefer colors with balanced lightness (not too dark, not too light)
                        lightness_score = 1.0 - abs(l - 0.4) * 1.5  # Prefer medium-dark colors

                        # Prefer colors with good saturation
                        saturation_score = min(s * 1.8, 1.0)  # Boost saturated colors more

                        # Calculate distance from already selected colors
                        min_dist_to_selected = float('inf')
                        for sel_color in selected_colors:
                            sel_hsl = sel_color['hsl']
                            # Calculate distance considering hue's circular nature
                            hue_diff = abs(h - sel_hsl[0])
                            hue_dist = min(hue_diff, 1.0 - hue_diff) * 3  # Hue is very important
                            light_dist = abs(l - sel_hsl[1]) * 2  # Lightness is important
                            sat_dist = abs(s - sel_hsl[2]) * 1  # Saturation less important
                            total_dist = hue_dist + light_dist + sat_dist

                            if total_dist < min_dist_to_selected:
                                min_dist_to_selected = total_dist

                        # Combine scores: diversity + quality
                        diversity_score = min_dist_to_selected / 6.0  # Normalize distance
                        quality_score = (lightness_score + saturation_score) / 2.0
                        total_score = diversity_score * 0.7 + quality_score * 0.3

                        if total_score > max_score:
                            max_score = total_score
                            best_candidate = pixel
                    
                    if best_candidate:
                        selected_colors.append(self._get_color_properties(best_candidate))
                    else:
                        break # No more candidates to add

                # Add count information back to the selected colors
                for color in selected_colors:
                    color['count'] = pixel_counts.get(color['rgb'], 1)
                
                # Sort by lightness for smooth dark-to-light transition
                selected_colors.sort(key=lambda c: c['lightness'])
                
                return selected_colors

        except Exception as e:
            logger.error(f"Error in max diversity extraction for {image_path}: {e}")
            return []

    def analyze_image_colors(self, image_path: Path) -> Dict:
        """
        Performs a full analysis on an image: main palette and analogous harmonies.
        """
        main_palette = self.extract_colors_max_diversity(image_path, max_colors=self.max_colors)
        
        analogous_palette = []
        if main_palette:
            # Generate analogous palette based on entire main palette
            analogous_palette = self.generate_detailed_analogous_palette(main_palette)
            
        return {
            'image_path': str(image_path),
            'main_palette': main_palette,
            'analogous_palette': analogous_palette,
        }

    def analyze_all_images(self) -> Dict:
        """Analyzes all images and generates rich HTML reports."""
        print("=" * 70)
        print("🎨 ADVANCED COLOR ANALYZER - Maximum Diversity Edition 🎨")
        print(f"🌈 {self.max_colors} High-Quality Colors | 25+ Diverse Analogous Suggestions")
        print("=" * 70)

        image_files = sorted([p for ext in self.image_extensions for p in self.images_folder.glob(ext)])
        if not image_files:
            print("❌ No images found!")
            return {}

        results = []
        html_files = []
        start_time = time.time()

        for i, image_file in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] Analyzing: {image_file.name}")
            result = self.analyze_image_colors(image_file)
            results.append(result)

            # html_path = self.save_html_to_palettes(image_file, result)
            # html_files.append(str(html_path))
            # print(f"  📄 HTML report saved: {html_path.name}")
            print(f"  ✅ Analysis completed for {image_file.name}")

        total_time = time.time() - start_time

        # print("\n" + "=" * 60)
        # print("HTML REPORTS GENERATED:")
        # for html_file in html_files:
        #     print(f"🎨 {Path(html_file).name}")
        print(f"\n✅ Processing completed successfully! {len(results)} images analyzed.")
        
        return {
            'results': results,
            'html_files': html_files,
            'summary': {
                'total_images': len(results),
                'total_time': round(total_time, 2)
            }
        }

    def save_html_to_palettes(self, image_path: Path, analysis_data: Dict) -> Path:
        """Saves the full analysis to an HTML file."""
        palettes_dir = Path("C:/shotdeck-main/palettes")
        palettes_dir.mkdir(exist_ok=True)
        html_filename, html_content = self.generate_beautiful_html(image_path, analysis_data)
        html_path = palettes_dir / html_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return html_path

    def generate_beautiful_html(self, image_path: Path, data: Dict) -> tuple[str, str]:
        """Generates a beautiful HTML page for the color analysis."""
        image_name = image_path.stem
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        html_filename = f"{image_name}_{timestamp}.html"
        
        main_palette = data.get('main_palette', [])
        analogous_palette = data.get('analogous_palette', [])

        # --- Helper for generating main palette cards ---
        def generate_color_cards(colors):
            cards_html = ""
            for i, color in enumerate(colors, 1):
                cards_html += f"""
                <div class="color-card">
                    <div class="color-display" style="background-color: {color['hex']};" onclick="copyToClipboard('{color['hex']}')"><div class="color-number">{i}</div></div>
                    <div class="color-info">
                        <div class="color-code" onclick="copyToClipboard('{color['hex']}')">{color['hex']}</div>
                    </div>
                </div>"""
            return cards_html

        # --- Helper for analogous harmony swatches ---
        def generate_analogous_swatches(colors):
            if not colors: return ""
            # Sort colors by lightness for smooth transition
            sorted_colors = sorted(colors, key=lambda c: c['lightness'])
            swatches_html = "<div class='harmony-card'><div class='harmony-swatches'>"

            # Display up to 25 diverse analogous colors
            displayed_count = 0
            for color in sorted_colors:
                if displayed_count >= 25:
                    break
                if displayed_count == 0:
                    # First color as base
                    swatches_html += f"<div class='swatch base' style='background-color: {color['hex']}' onclick=\"copyToClipboard('{color['hex']}')\" title='Base Color: {color['hex']}'></div>"
                else:
                    swatches_html += f"<div class='swatch' style='background-color: {color['hex']}' onclick=\"copyToClipboard('{color['hex']}')\" title='Suggestion: {color['hex']}'></div>"
                displayed_count += 1

            swatches_html += "</div></div>"
            return swatches_html

        # --- Main HTML Structure ---
        html_content = f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 تحلیل رنگ جامع - {image_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Vazir:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{ background: #f0f2f5; font-family: 'Vazir', sans-serif; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: #fff; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 2.5rem; }}
        .section-title {{ font-size: 1.8rem; font-weight: 700; color: #333; margin: 30px 30px 20px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
        .palette {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; padding: 30px; }}
        .color-card {{ background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.07); transition: all 0.3s ease; border: 1px solid #e9ecef; text-align: center; }}
        .color-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }}
        .color-display {{ height: 120px; cursor: pointer; display: flex; align-items: center; justify-content: center; position: relative; }}
        .color-number {{ color: white; font-size: 1.5rem; font-weight: 700; text-shadow: 0 1px 3px rgba(0,0,0,0.6); }}
        .color-info {{ padding: 15px; }}
        .color-code {{ background: #f8f9fa; padding: 8px 12px; border-radius: 8px; font-family: 'Courier New', monospace; cursor: pointer; font-size: 0.9rem; }}
        /* Styles for Analogous Palette */
        .harmony-card {{ background: #f8f9fa; border-radius: 15px; padding: 20px; margin: 0 30px 30px; border: 1px solid #e9ecef; }}
        .harmony-swatches {{ display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 15px; }}
        .swatch {{ width: 70px; height: 70px; border-radius: 50%; cursor: pointer; border: 4px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.2s; }}
        .swatch:hover {{ transform: scale(1.1); }}
        .swatch.base {{ width: 80px; height: 80px; border-color: #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>تحلیل رنگ جامع</h1><div class="image-info">{image_name}</div></div>
        <h2 class="section-title">🎨 پالت اصلی با حداکثر تنوع رنگی</h2>
        <div class="palette">{generate_color_cards(main_palette)}</div>
        <h2 class="section-title">💡 پیشنهاد پالت رنگ‌های مجاور (Analogous)</h2>
        <div class="harmonies-container">{generate_analogous_swatches(analogous_palette)}</div>
    </div>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => alert('کد رنگ کپی شد: ' + text));
        }}
    </script>
</body>
</html>"""
        return html_filename, html_content

def main():
    """Main function for command line usage."""
    images_folder = sys.argv[1] if len(sys.argv) > 1 else "C:/shotdeck-main/search_service/images"
    if not Path(images_folder).exists():
        print(f"❌ Images folder not found: {images_folder}")
        return

    processor = UltimateColorProcessor(images_folder=images_folder, max_colors=15)
    processor.analyze_all_images()

if __name__ == "__main__":
    main()
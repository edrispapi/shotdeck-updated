#!/usr/bin/env python3
import os
import sys
import django

# Add the Django project to the Python path
sys.path.append('/service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import Image, Movie

def show_sample_data():
    print('=== 10 SAMPLE IMPORTED DATA WITH FULL METADATA ===')
    print()
    
    # Get 10 recent images with full metadata
    sample_images = Image.objects.order_by('-id')[:10]
    
    for i, img in enumerate(sample_images, 1):
        print(f'[{i}] Image Slug: {img.slug}')
        print(f'    Title: {img.title if img.title else "N/A"}')
        print(f'    Movie: {img.movie.title if img.movie else "None"}')
        print(f'    Year: {img.movie.year if img.movie and img.movie.year else "N/A"}')
        print(f'    Image URL: {img.image_url}')
        print(f'    Media Type: {img.media_type.value if img.media_type else "None"}')
        print(f'    Director: {img.director.value if img.director else "None"}')
        print(f'    Cinematographer: {img.cinematographer.value if img.cinematographer else "None"}')
        print(f'    Genre: {[g.value for g in img.genre.all()] if img.genre.exists() else "None"}')
        print(f'    Actor: {img.actor.value if img.actor else "None"}')
        print(f'    Camera: {img.camera.value if img.camera else "None"}')
        print(f'    Lens: {img.lens.value if img.lens else "None"}')
        print(f'    Lighting: {img.lighting.value if img.lighting else "None"}')
        print(f'    Shot Type: {img.shot_type.value if img.shot_type else "None"}')
        print(f'    Composition: {img.composition.value if img.composition else "None"}')
        print(f'    Aspect Ratio: {img.aspect_ratio.value if img.aspect_ratio else "None"}')
        print(f'    Color: {img.color.value if img.color else "None"}')
        print(f'    Description: {img.description[:100] if img.description else "None"}...')
        print('    ' + '='*60)
        print()
    
    print('=== IMPORT PROGRESS SUMMARY ===')
    print(f'Total Images: {Image.objects.count()}')
    print(f'Total Movies: {Movie.objects.count()}')
    print(f'Progress: {(Image.objects.count() / 28189) * 100:.1f}%')

if __name__ == '__main__':
    show_sample_data()

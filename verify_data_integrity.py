#!/usr/bin/env python3
import os
import sys
import django
import json

# Add the Django project to the Python path
sys.path.append('/service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.images.models import Image

def verify_data_integrity():
    print("=== DATABASE vs JSON VERIFICATION ===")
    
    # Get a sample image from database
    img = Image.objects.filter(slug__startswith='3ujb4r4v').first()
    if not img:
        print("Image not found in database")
        return
    
    print(f"Database Image: {img.slug}")
    print(f"Database Movie: {img.movie.title if img.movie else 'None'}")
    print(f"Database Media Type: {img.media_type.value if img.media_type else 'None'}")
    print(f"Database Director: {img.director.value if img.director else 'None'}")
    print(f"Database Cinematographer: {img.cinematographer.value if img.cinematographer else 'None'}")
    print(f"Database Genre: {[g.value for g in img.genre.all()] if img.genre.exists() else 'None'}")
    print()
    
    # Check JSON file
    json_path = '/host_data/dataset/shot_json_data/3UJB4R4V.json'
    if not os.path.exists(json_path):
        print("JSON file not found")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    details = data['data']['details']
    print("=== SOURCE JSON DATA ===")
    print(f"JSON Movie: {details['title']['values'][0]['display_value']}")
    print(f"JSON Media Type: {details['media_type']['values'][0]['display_value']}")
    print(f"JSON Year: {details['year']['values'][0]['display_value']}")
    
    # Check title_info section
    title_info = details.get('title_info', {})
    if 'director' in title_info:
        print(f"JSON Director: {title_info['director']['values'][0]['display_value']}")
    if 'cinematographer' in title_info:
        print(f"JSON Cinematographer: {title_info['cinematographer']['values'][0]['display_value']}")
    if 'genre' in title_info:
        print(f"JSON Genre: {[g['display_value'] for g in title_info['genre']['values']]}")
    
    print()
    print("=== VERIFICATION RESULT ===")
    
    # Compare movie
    json_movie = details['title']['values'][0]['display_value']
    db_movie = img.movie.title if img.movie else None
    movie_match = json_movie == db_movie
    print(f"Movie Match: {movie_match} ({json_movie} == {db_movie})")
    
    # Compare media type
    json_media = details['media_type']['values'][0]['display_value']
    db_media = img.media_type.value if img.media_type else None
    media_match = json_media == db_media
    print(f"Media Type Match: {media_match} ({json_media} == {db_media})")
    
    # Compare genre
    json_genre = [g['display_value'] for g in title_info['genre']['values']]
    db_genre = [g.value for g in img.genre.all()]
    genre_match = sorted(json_genre) == sorted(db_genre)
    print(f"Genre Match: {genre_match} ({json_genre} == {db_genre})")
    
    # Compare director
    json_director = title_info['director']['values'][0]['display_value']
    db_director = img.director.value if img.director else None
    director_match = json_director == db_director
    print(f"Director Match: {director_match} ({json_director} == {db_director})")
    
    # Compare cinematographer
    json_cinematographer = title_info['cinematographer']['values'][0]['display_value']
    db_cinematographer = img.cinematographer.value if img.cinematographer else None
    cinematographer_match = json_cinematographer == db_cinematographer
    print(f"Cinematographer Match: {cinematographer_match} ({json_cinematographer} == {db_cinematographer})")
    
    print()
    print("=== OVERALL VERIFICATION ===")
    all_matches = movie_match and media_match and genre_match and director_match and cinematographer_match
    print(f"All Data Matches: {all_matches}")
    
    if all_matches:
        print("✅ DATA INTEGRITY VERIFIED: All imported data matches source JSON metadata!")
    else:
        print("❌ DATA INTEGRITY ISSUES: Some data does not match source JSON")

if __name__ == "__main__":
    verify_data_integrity()

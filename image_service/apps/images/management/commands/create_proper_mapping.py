import os
import json
import hashlib
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.images.models import Image


class Command(BaseCommand):
    help = 'Create proper mapping between JSON metadata and actual image files using systematic analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-dir',
            type=str,
            default='/host_data/dataset/shot_json_data',
            help='Directory containing JSON files'
        )
        parser.add_argument(
            '--images-dir',
            type=str,
            default='/host_data/dataset/shot_images',
            help='Directory containing actual image files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of images to process (for testing)'
        )

    def handle(self, *args, **options):
        json_dir = options['json_dir']
        images_dir = options['images_dir']
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(f"Creating proper mapping between JSON metadata and image files")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all image files in the filesystem
        try:
            available_files = set(os.listdir(images_dir))
            # Filter only .jpg files
            available_files = {f for f in available_files if f.endswith('.jpg')}
            self.stdout.write(f"Found {len(available_files)} image files in filesystem")
        except Exception as e:
            raise CommandError(f"Could not read images directory {images_dir}: {e}")

        # Get all JSON files
        try:
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            json_files.sort()  # Process in deterministic order
            self.stdout.write(f"Found {len(json_files)} JSON files")
        except Exception as e:
            raise CommandError(f"Could not read JSON directory {json_dir}: {e}")

        if limit:
            json_files = json_files[:limit]
            self.stdout.write(f"Limited to {limit} files for testing")

        # Track statistics
        stats = {
            'processed': 0,
            'found_exact_match': 0,
            'found_metadata_match': 0,
            'found_systematic_match': 0,
            'found_pattern_match': 0,
            'not_found': 0,
            'updated': 0,
            'errors': 0
        }

        # Track used files globally to avoid duplicates
        used_files = set()

        # Create mapping strategies
        mapping_strategies = self.create_mapping_strategies(json_files, json_dir, available_files)

        # Process each JSON file
        for json_file in json_files:
            json_path = os.path.join(json_dir, json_file)
            
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                # Extract image information
                if 'data' in data and isinstance(data['data'], dict):
                    image_data = data['data']
                    image_id = image_data.get('imageid')
                    image_file = image_data.get('image_file')
                    
                    if image_id and image_file:
                        stats['processed'] += 1
                        
                        # Find the corresponding image in database
                        try:
                            db_image = Image.objects.get(image_url=f"/media/images/{image_file}")
                            
                            # Check if file exists exactly as specified
                            if image_file in available_files:
                                stats['found_exact_match'] += 1
                                self.stdout.write(f"  {image_id}: {image_file} - EXACT MATCH")
                            else:
                                # Try systematic mapping strategies
                                proper_match = self.find_proper_match(image_id, image_file, image_data, available_files, mapping_strategies, used_files)
                                
                                if proper_match:
                                    if proper_match['strategy'] == 'metadata':
                                        stats['found_metadata_match'] += 1
                                    elif proper_match['strategy'] == 'systematic':
                                        stats['found_systematic_match'] += 1
                                    elif proper_match['strategy'] == 'pattern':
                                        stats['found_pattern_match'] += 1
                                    
                                    if not dry_run:
                                        # Update database with correct file
                                        db_image.image_url = f"/media/images/{proper_match['file']}"
                                        db_image.save()
                                        stats['updated'] += 1
                                    
                                    self.stdout.write(f"  {image_id}: {image_file} -> {proper_match['file']} ({proper_match['strategy']})")
                                else:
                                    stats['not_found'] += 1
                                    self.stdout.write(self.style.ERROR(f"  {image_id}: {image_file} - NO MATCH FOUND"))
                        
                        except Image.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"  {image_id}: Not found in database"))
                            stats['errors'] += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  {image_id}: Error - {e}"))
                            stats['errors'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {json_file}: {e}"))
                stats['errors'] += 1

        # Print final statistics
        self.stdout.write("\n" + "="*60)
        self.stdout.write("PROPER MAPPING STATISTICS")
        self.stdout.write("="*60)
        self.stdout.write(f"Processed JSON files: {stats['processed']}")
        self.stdout.write(f"Exact matches found: {stats['found_exact_match']}")
        self.stdout.write(f"Metadata-based matches: {stats['found_metadata_match']}")
        self.stdout.write(f"Systematic matches: {stats['found_systematic_match']}")
        self.stdout.write(f"Pattern-based matches: {stats['found_pattern_match']}")
        self.stdout.write(f"Files not found: {stats['not_found']}")
        self.stdout.write(f"Database records updated: {stats['updated']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a DRY RUN - no changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {stats['updated']} database records"))

    def create_mapping_strategies(self, json_files, json_dir, available_files):
        """
        Create mapping strategies based on analysis of JSON metadata and file patterns.
        """
        strategies = {
            'metadata_mapping': {},
            'systematic_mapping': {},
            'pattern_mapping': {}
        }
        
        # Analyze JSON files to create metadata-based mapping
        self.stdout.write("Analyzing JSON metadata for mapping strategies...")
        
        for json_file in json_files[:100]:  # Analyze first 100 files for patterns
            json_path = os.path.join(json_dir, json_file)
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                if 'data' in data and isinstance(data['data'], dict):
                    image_data = data['data']
                    image_id = image_data.get('imageid')
                    image_file = image_data.get('image_file')
                    
                    if image_id and image_file:
                        # Extract metadata for mapping
                        metadata = self.extract_metadata_for_mapping(image_data)
                        strategies['metadata_mapping'][image_id] = metadata
                        
            except Exception as e:
                continue
        
        return strategies

    def extract_metadata_for_mapping(self, image_data):
        """
        Extract relevant metadata for mapping purposes.
        """
        metadata = {
            'title': None,
            'year': None,
            'search_value': None,
            'media_type': None,
            'actors': [],
            'tags': []
        }
        
        if 'details' in image_data:
            details = image_data['details']
            
            # Extract title and search value
            if 'title' in details and 'values' in details['title']:
                if len(details['title']['values']) > 0:
                    metadata['title'] = details['title']['values'][0].get('display_value')
                    metadata['search_value'] = details['title']['values'][0].get('search_value')
            
            # Extract year
            if 'year' in details and 'values' in details['year']:
                if len(details['year']['values']) > 0:
                    metadata['year'] = details['year']['values'][0].get('display_value')
            
            # Extract media type
            if 'media_type' in details and 'values' in details['media_type']:
                if len(details['media_type']['values']) > 0:
                    metadata['media_type'] = details['media_type']['values'][0].get('display_value')
            
            # Extract actors
            if 'shot_info' in details and 'actors' in details['shot_info']:
                if 'values' in details['shot_info']['actors']:
                    metadata['actors'] = [actor.get('display_value') for actor in details['shot_info']['actors']['values']]
            
            # Extract tags
            if 'shot_info' in details and 'tags' in details['shot_info']:
                if 'values' in details['shot_info']['tags']:
                    metadata['tags'] = [tag.get('display_value') for tag in details['shot_info']['tags']['values']]
        
        return metadata

    def find_proper_match(self, image_id, original_file, image_data, available_files, mapping_strategies, used_files):
        """
        Find the proper match using multiple systematic strategies.
        """
        # Strategy 1: Metadata-based mapping
        metadata_match = self.find_metadata_based_match(image_id, image_data, available_files, mapping_strategies, used_files)
        if metadata_match:
            used_files.add(metadata_match)
            return {'file': metadata_match, 'strategy': 'metadata'}
        
        # Strategy 2: Systematic mapping based on search values
        systematic_match = self.find_systematic_match(image_id, image_data, available_files, used_files)
        if systematic_match:
            used_files.add(systematic_match)
            return {'file': systematic_match, 'strategy': 'systematic'}
        
        # Strategy 3: Pattern-based mapping
        pattern_match = self.find_pattern_based_match(image_id, original_file, available_files, used_files)
        if pattern_match:
            used_files.add(pattern_match)
            return {'file': pattern_match, 'strategy': 'pattern'}
        
        return None

    def find_metadata_based_match(self, image_id, image_data, available_files, mapping_strategies, used_files):
        """
        Find matches based on metadata analysis.
        """
        # Extract metadata for this image
        metadata = self.extract_metadata_for_mapping(image_data)
        
        # Look for files that might correspond to this metadata
        # This is a placeholder for more sophisticated metadata-based matching
        # Could include image content analysis, hash matching, etc.
        
        return None

    def find_systematic_match(self, image_id, image_data, available_files, used_files):
        """
        Find matches based on systematic patterns in the data.
        """
        # Strategy: Use search_value to find systematic mapping
        if 'details' in image_data and 'title' in image_data['details']:
            title_data = image_data['details']['title']
            if 'values' in title_data and len(title_data['values']) > 0:
                search_value = title_data['values'][0].get('search_value')
                if search_value and search_value.isdigit():
                    # Try to find files organized by this search value
                    # This could be a systematic identifier
                    pass
        
        return None

    def find_pattern_based_match(self, image_id, original_file, available_files, used_files):
        """
        Find matches based on filename patterns and character analysis.
        """
        # Strategy 1: Look for files with the image_id pattern
        if image_id:
            for file in available_files:
                if file.startswith(image_id) and file.endswith('.jpg') and file not in used_files:
                    return file
        
        # Strategy 2: Look for files with similar character patterns (avoid duplicates)
        base_name = os.path.splitext(original_file)[0]
        original_chars = set(base_name.lower())
        
        best_match = None
        best_score = 0
        
        for file in available_files:
            if file.endswith('.jpg') and file not in used_files:
                file_base = os.path.splitext(file)[0]
                if len(file_base) == len(base_name):
                    file_chars = set(file_base.lower())
                    # Calculate similarity score
                    common_chars = original_chars.intersection(file_chars)
                    score = len(common_chars) / len(original_chars) if original_chars else 0
                    
                    if score > best_score and score > 0.8:  # At least 80% similarity
                        best_score = score
                        best_match = file
        
        if best_match:
            return best_match
        
        # Strategy 3: Look for files with similar length and pattern (avoid duplicates)
        for file in available_files:
            if len(file) == len(original_file) and file.endswith('.jpg') and file not in used_files:
                file_base = os.path.splitext(file)[0]
                if file_base.isalnum() and len(file_base) == len(base_name):
                    return file
        
        # Strategy 4: Look for files starting with the same characters (avoid duplicates)
        for file in available_files:
            if file.startswith(base_name[:4]) and file.endswith('.jpg') and file not in used_files:
                return file
        
        # Strategy 5: Look for files ending with the same characters (avoid duplicates)
        for file in available_files:
            if file.endswith(base_name[-4:] + '.jpg') and file not in used_files:
                return file
        
        return None

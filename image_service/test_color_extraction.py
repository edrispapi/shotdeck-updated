#!/usr/bin/env python3
import sys
import os
sys.path.append('/service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.images.models import Image, ColorOption
from apps.images.management.commands.import_images_with_metadata import Command

# Test the full color extraction process
cmd = Command()
json_data = {
    'data': {
        'details': {
            'shot_info': {
                'color': {
                    'values': [
                        {'display_value': 'Desaturated', 'search_value': 'Desaturated'},
                        {'display_value': 'Black and White', 'search_value': 'Black+and+White'}
                    ]
                }
            }
        }
    }
}

details = json_data['data']['details']
shot_info = details.get('shot_info', {})

# Test the color extraction
color_data = shot_info.get('color', {})
color_values = color_data.get('values', [])
print('Color values:', [v['display_value'] for v in color_values])

if color_values:
    first_color = color_values[0]['display_value']
    print(f'First color: {first_color}')
    color_option = cmd._get_or_create_option(ColorOption, first_color)
    print(f'Created color option: {color_option.value}')
    
    # Test if this would be in options
    options = {}
    options['color'] = color_option
    print(f'Options color: {options["color"].value if options["color"] else None}')
else:
    print('No color values found')

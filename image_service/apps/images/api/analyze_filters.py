import requests
import json

# Get filters data
response = requests.get('http://localhost:9000/api/images/filters/')
if response.status_code == 200:
    data = response.json()
    
    print('=== FILTERS API ANALYSIS ===')
    
    # Check color options
    color_options = data.get('data', {}).get('color', [])
    print(f'Color options in API: {len(color_options)}')
    if color_options:
        print('Sample color options:')
        for option in color_options[:5]:
            print(f'  - {option.get(value, N/A)}')
    
    # Check other categories
    categories = ['genre', 'shot_type', 'lighting', 'aspect_ratio']
    for cat in categories:
        options = data.get('data', {}).get(cat, [])
        print(f'{cat} options in API: {len(options)}')
        
        # Check if options match database for small categories
        if len(options) < 20:
            print(f'  Sample {cat} options:')
            for option in options[:3]:
                print(f'    - {option.get(value, N/A)}')
    
    # Check smart filtering info
    smart = data.get('smart_filtering', {})
    print(f'\nSmart filtering enabled: {smart.get(smart_filtering_enabled, False)}')
    working_categories = smart.get('working_categories', [])
    empty_categories = smart.get('categories_currently_empty', [])
    print(f'Working categories: {len(working_categories)}')
    print(f'Empty categories: {len(empty_categories)}')
    
    # Check if color is in empty categories (it shouldn't be)
    if 'color' in empty_categories:
        print('❌ ERROR: Color is listed as empty but we have color data!')
    else:
        print('✅ Color is correctly listed as working')
        
else:
    print(f'API Error: {response.status_code}')
    print(response.text[:500])

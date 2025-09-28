"""
Utility functions for Deck Service
"""

def postprocess_schema(result, generator, request, public):
    """
    Post-process the OpenAPI schema to customize it for Deck Service
    """
    # Remove /api/v1/ prefix from all paths to show clean URLs in Swagger UI
    new_paths = {}
    for path, path_item in result['paths'].items():
        # Remove /api/v1/ prefix from paths
        if path.startswith('/api/v1/'):
            new_path = path.replace('/api/v1/', '/api/', 1)
        else:
            new_path = path

        # Only keep GET methods, remove POST, PUT, DELETE, PATCH
        if isinstance(path_item, dict):
            filtered_methods = {}
            for method, operation in path_item.items():
                if method.upper() == 'GET':
                    filtered_methods[method] = operation
            if filtered_methods:  # Only add path if it has GET method
                new_paths[new_path] = filtered_methods
        else:
            new_paths[new_path] = path_item

    result['paths'] = new_paths

    # Update the schema info
    result['info']['title'] = 'Shotdeck Deck Service API'
    result['info']['description'] = 'API for managing image decks and collections'

    return result
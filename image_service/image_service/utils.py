"""
Utility functions for Image Service
"""

def postprocess_schema(result, generator, request, public):
    """
    Post-process the OpenAPI schema to customize it for Image Service
    """
    # Remove /api/v1/ prefix from all paths to show clean URLs in Swagger UI
    new_paths = {}
    for path, path_item in result['paths'].items():
        # Skip all options endpoints
        if '/api/options/' in path:
            continue

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

                    # Remove legacy parameters from GET operations
                    if 'parameters' in filtered_methods[method]:
                        filtered_params = []
                        legacy_params = {'q', 'release_year', 'release_year__gte', 'release_year__lte', 'page'}

                        for param in filtered_methods[method]['parameters']:
                            param_name = param.get('name', '')
                            if param_name not in legacy_params:
                                filtered_params.append(param)

                        filtered_methods[method]['parameters'] = filtered_params

            if filtered_methods:  # Only add path if it has GET method
                new_paths[new_path] = filtered_methods
        else:
            new_paths[new_path] = path_item

    result['paths'] = new_paths

    # Update the schema info
    result['info']['title'] = 'Shotdeck Image Service API'
    result['info']['description'] = 'API for managing images and their metadata'

    return result
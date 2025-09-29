"""
Utility functions for Search Service
"""

from django.core.cache import cache
import json
import hashlib

def cache_search_result(cache_key=None, result=None, timeout=3600):
    """
    Cache search result with given key and timeout, or as a decorator
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments if not provided
            key = cache_key
            if key is None:
                # Use function name and arguments to generate key
                key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

            # Check cache first
            cached_result = get_cached_search_result(key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache the result
            try:
                if isinstance(result, (dict, list)):
                    cache_value = json.dumps(result)
                else:
                    cache_value = str(result)
                cache.set(key, cache_value, timeout)
            except Exception as e:
                print(f"Error caching search result: {e}")

            return result
        return wrapper

    # If called with cache_key and result, act as regular function
    if cache_key is not None and result is not None:
        try:
            if isinstance(result, (dict, list)):
                cache_value = json.dumps(result)
            else:
                cache_value = str(result)
            cache.set(cache_key, cache_value, timeout)
            return True
        except Exception as e:
            print(f"Error caching search result: {e}")
            return False
    else:
        # Act as decorator
        return decorator

def get_cached_search_result(cache_key):
    """
    Get cached search result by key
    """
    try:
        cached_value = cache.get(cache_key)
        if cached_value:
            # Try to parse as JSON, if fails return as string
            try:
                return json.loads(cached_value)
            except (json.JSONDecodeError, TypeError):
                return cached_value
        return None
    except Exception as e:
        print(f"Error getting cached search result: {e}")
        return None

def generate_cache_key(query_params, user_id=None):
    """
    Generate a unique cache key from search parameters
    """
    # Create a string representation of the query parameters
    params_str = str(sorted(query_params.items()))

    # Add user_id if provided for user-specific caching
    if user_id:
        params_str += f"_user_{user_id}"

    # Create MD5 hash of the parameters
    cache_key = hashlib.md5(params_str.encode()).hexdigest()
    return f"search_{cache_key}"

def cache_user_data(user_id, user_data, timeout=3600):
    """
    Cache user data with given user_id and timeout
    """
    try:
        cache_key = f"user_data_{user_id}"
        if isinstance(user_data, (dict, list)):
            cache_value = json.dumps(user_data)
        else:
            cache_value = str(user_data)

        cache.set(cache_key, cache_value, timeout)
        return True
    except Exception as e:
        print(f"Error caching user data: {e}")
        return False

def get_cached_user_data(user_id):
    """
    Get cached user data by user_id
    """
    try:
        cache_key = f"user_data_{user_id}"
        cached_value = cache.get(cache_key)
        if cached_value:
            # Try to parse as JSON, if fails return as string
            try:
                return json.loads(cached_value)
            except (json.JSONDecodeError, TypeError):
                return cached_value
        return None
    except Exception as e:
        print(f"Error getting cached user data: {e}")
        return None

def postprocess_schema(result, generator, request, public):
    """
    Post-process the OpenAPI schema to customize it for Search Service
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
    result['info']['title'] = 'Shotdeck Search Service API'
    result['info']['description'] = 'API for advanced image search'

    return result
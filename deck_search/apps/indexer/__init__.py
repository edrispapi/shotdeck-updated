# این فایل باید خالی باشد تا از AppRegistryNotReady جلوگیری شود

def get_image_indexer():
    """Lazy import to avoid circular dependencies"""
    from apps.indexer.indexer import get_image_indexer as _get_indexer
    return _get_indexer()

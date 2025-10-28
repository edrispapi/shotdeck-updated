#!/usr/bin/env python
from elasticsearch_dsl.connections import connections
from elasticsearch.exceptions import NotFoundError
from django.conf import settings
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.search.documents import ImageDocument

def reset_elasticsearch():
    # Connect to Elasticsearch
    connections.create_connection(
        hosts=[f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"]
    )
    
    # Delete the index if it exists
    try:
        ImageDocument._index.delete()
        print("Deleted existing index")
    except NotFoundError:
        print("Index did not exist")
    
    # Create new index with mapping
    ImageDocument.init()
    print("Created new index with mapping")

if __name__ == "__main__":
    reset_elasticsearch()
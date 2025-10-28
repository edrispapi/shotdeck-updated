from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for all ViewSets
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'page_size': self.page_size
        })


class ImagePagination(StandardPagination):
    """
    Specialized pagination for Image ViewSet
    """
    page_size = 50
    max_page_size = 200


class MoviePagination(StandardPagination):
    """
    Specialized pagination for Movie ViewSet
    """
    page_size = 30
    max_page_size = 100


class TagPagination(StandardPagination):
    """
    Specialized pagination for Tag ViewSet
    """
    page_size = 100
    max_page_size = 500


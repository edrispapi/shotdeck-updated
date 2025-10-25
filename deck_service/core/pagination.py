from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """Project-level pagination for deck_service.

    Default and max page size set to 20, clients may pass `page_size` (capped at 20).
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20

from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """PageNumberPagination that allows clients to request a page_size up to a max.

    - default page_size = 20
    - page_size_query_param = 'page_size' allows client control
    - max_page_size = 20 (per-view logic may lower this further)
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20

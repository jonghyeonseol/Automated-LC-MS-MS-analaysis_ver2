"""
Custom pagination classes for the API
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size.

    Allows clients to specify page size via 'page_size' query parameter.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

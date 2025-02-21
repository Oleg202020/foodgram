from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Настройка пагинации в классе."""
    page_size_query_param = 'limit'
    page_size = 6

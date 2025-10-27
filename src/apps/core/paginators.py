from rest_framework import pagination


class CustomLimitOffsetPagination(pagination.LimitOffsetPagination):
    default_limit = 50

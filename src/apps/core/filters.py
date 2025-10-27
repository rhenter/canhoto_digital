from django_filters.rest_framework import Filter


class CustomBooleanFilter(Filter):
    def filter(self, qs, value):
        if value in (True, 'True', 'true', '1'):
            filter_value = True
        elif value in (False, 'False', 'false', '0'):
            filter_value = False
        else:
            filter_value = None

        if filter_value is None:
            return super().filter(qs, value)

        return qs.filter(**{self.field_name: filter_value})

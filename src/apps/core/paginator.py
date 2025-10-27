import logging

from django.contrib.admin.views.main import ChangeList, ORDER_VAR
from django.core.paginator import Paginator
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class IntPlus(int):
    def __str__(self):
        return '{}+'.format(int.__str__(self))


class NoPkChangeList(ChangeList):
    def get_ordering(self, request, queryset):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, WE REMOVE the primary
        key ordering field.
        """
        params = self.params
        ordering = list(self.model_admin.get_ordering(request) or self._get_default_ordering())
        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue  # No 'admin_order_field', skip it
                    # reverse order if order_field has already "-" as prefix
                    if order_field.startswith('-') and pfx == "-":
                        ordering.append(order_field[1:])
                    else:
                        ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue  # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        ordering.extend(queryset.query.order_by)

        # Ensure that the primary key is systematically present in the list of
        # ordering fields so we can guarantee a deterministic order across all
        # database backends.
        # pk_name = self.lookup_opts.pk.name
        # if not (set(ordering) & {'pk', '-pk', pk_name, '-' + pk_name}):
        #     # The two sets do not intersect, meaning the pk isn't present. So
        #     # we add it.
        #     ordering.append('-pk')

        return ordering


class LargeTablePaginator(Paginator):
    LIMIT = 10000

    @cached_property
    def count(self):
        return 1000

        try:
            limit = self.LIMIT
            total = self.object_list.order_by()[:limit].count()
            # ^-- User order_by() to remove any ordering and
            # count objects as quickly as possible. (Shouldn't
            # SQL optimize the query regardless of ordering?)
            return total if total < limit else IntPlus(total)
        except (AttributeError, TypeError):
            # AttributeError if object_list has no count() method.
            # TypeError if object_list.count() requires arguments
            # (i.e. is of type list).
            return len(self.object_list)

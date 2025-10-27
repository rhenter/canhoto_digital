from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _


class AdminFilterMixin(SimpleListFilter):
    search_terms_ignore = ['q', 'all']

    def clean_query(self, request):
        search_dict = request.GET.dict()
        for search_term in self.search_terms_ignore:
            if search_dict.get(search_term, None) is not None:
                del search_dict[search_term]
        return search_dict

    def get_queryset(self, request, model_admin):
        query_dict = self.clean_query(request)
        queryset = model_admin.get_queryset(request)
        if query_dict:
            queryset = queryset.filter(**query_dict)
        return queryset


class PlantAreaAdminFilter(AdminFilterMixin):
    title = _('Area')
    parameter_name = 'section__area'

    def lookups(self, request, model_admin):
        querystring = self.clean_query(request)
        qs = self.get_queryset(request, model_admin).distinct()
        results = []
        added = []
        for setup in qs:
            if setup.section.area in added:
                continue

            area_name = setup.section.area.name
            if not querystring:
                area_name = str(setup.section.area)
            results.append((setup.section.area.id, area_name))
            added.append(setup.section.area)
        return results

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(section__area__exact=self.value())


class SectionAdminFilter(AdminFilterMixin):
    title = _('Section')

    parameter_name = 'section'

    def lookups(self, request, model_admin):
        querystring = self.clean_query(request)
        qs = self.get_queryset(request, model_admin).order_by('section__name').distinct()
        results = []
        added = []
        for setup in qs:
            if setup.section in added:
                continue

            section_name = setup.section.name
            if not querystring:
                plant_slug = setup.section.area.plant.slug.replace('plc_', '')
                area_code = setup.section.area.code.upper().replace('_', ' ')
                section_name = f"{plant_slug.upper()}/{area_code}/{setup.section.name}"
            results.append((setup.section.id, section_name))
            added.append(setup.section)
        return results

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(section__exact=self.value()).order_by(
                'section__name'
            )

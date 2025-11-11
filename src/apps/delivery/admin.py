from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.core.templatetags.app_utils import cep_mask
from .models import Delivery, ProofOfDelivery, ProofOfDeliveryPhoto


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "_invoice_number",
        "status",
        "assigned_to",
        "_created_at",
        "_delivery_at",
        "pods_link",
    )
    search_fields = ("invoice__number", "invoice__key")
    list_filter = (
        "created_at",
        "delivery_at",
        "assigned_to",
        "status",
        "invoice__company"
    )
    fieldsets = (
        ("NF-e DATA", {
            'fields': ("invoice", "invoice_details",),
        }),
        (_('DELIVERY DATA'), {
            'fields': (
                "status",
                "delivery_at",
                "assigned_to",
                "invoice_address",
                "observations",
            ),
        }),
    )
    autocomplete_fields = ['invoice']
    readonly_fields = ["created_at", "delivery_at", "invoice_details", "invoice_address"]

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        inv_id = request.GET.get("invoice")
        if inv_id:
            initial["invoice"] = inv_id
        return initial

    def _created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    _created_at.short_description = _('Created at')
    _created_at.admin_order_field = 'created_at'

    def _delivery_at(self, obj):
        if not obj.delivery_at:
            return ""
        return obj.delivery_at.strftime('%Y-%m-%d %H:%M')

    _delivery_at.short_description = _('Delivery at')
    _delivery_at.admin_order_field = 'delivery_at'

    def _invoice_number(self, obj):
        return f"{obj.invoice.number}/{obj.invoice.series}"

    def pods_link(self, obj):
        url = reverse('admin:delivery_proofofdelivery_changelist')
        query = f"?delivery__id__exact={obj.id}"
        return mark_safe(f'<a class="button" href="{url}{query}">{_('List PODs')}</a>')

    pods_link.short_description = _('PODs')

    def invoice_details(self, obj):
        if not obj or not getattr(obj, "invoice_id", None):
            return "Selecione uma NF-e para visualizar os dados…"
        inv = obj.invoice
        return mark_safe(
            f"<b>{_('Number/Series')}:</b> {inv.number}/{getattr(inv, 'series', '')} <br />"
            f"<b>{_('Key')}:</b> {inv.key}  <br />"
            f"<b>{_('Total Value')}:</b> R$ {inv.total_value}  <br />"
            f"<b>{_('Recipient Name')}:</b> {getattr(inv, 'recipient_name', '')}   <br />"
        )

    invoice_details.allow_tags = True
    invoice_details.short_description = _("Identification")

    def invoice_address(self, obj):
        if not obj or not getattr(obj, "invoice_id", None):
            return ""
        inv = obj.invoice
        return mark_safe(
            f"{inv.recipient_address_street}, "
            f"{inv.recipient_address_number} · <br />"
            f"{inv.recipient_address_neighborhood} - "
            f"{inv.recipient_address_city} - "
            f"{inv.recipient_address_uf.upper()} <br />"
            f"{cep_mask(inv.recipient_address_zip_code)} <br />"
        )

    invoice_address.allow_tags = True
    invoice_address.short_description = _("Delivery Address")


class ProofOfDeliveryPhotoInline(admin.TabularInline):
    model = ProofOfDeliveryPhoto
    extra = 0
    fields = ["image", ]


@admin.register(ProofOfDelivery)
class ProofOfDeliveryAdmin(GISModelAdmin):
    list_display = (
        "id",
        "delivery",
        "received_by_name",
        "signed_at_server",
        "status",
    )
    search_fields = ("delivery__invoice__number", "received_by_name")
    list_filter = ("signed_at_server",)
    readonly_fields = ["signed_at_server", "created_at", "delivery_assigned_to", "location_coords"]
    fields = [
        "delivery",
        "delivery_assigned_to",
        "status",
        "observations",
        "received_by_name",
        "received_by_document",
        "signed_at",
        "signed_at_server",
        "location_coords",
        "location",
        "signature_image",
        "meta",
    ]
    inlines = [ProofOfDeliveryPhotoInline]
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 7,
            'default_lon': -44.18,
            'default_lat': -22.54,
            'map_width': 800,
            'map_height': 500,
        }
    }

    def delivery_assigned_to(self, obj):
        if not obj or not getattr(obj, "delivery_id", None):
            return "—"
        user = getattr(obj.delivery, "assigned_to", None)
        return str(user) if user else "—"

    delivery_assigned_to.short_description = _("Assigned to")

    def location_coords(self, obj):
        if not obj or not getattr(obj, "location", None):
            return "—"
        try:
            # GeoDjango PointField stores as (lon, lat)
            lat = obj.location.y
            lon = obj.location.x
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
            return mark_safe(f"{lat:.6f}, {lon:.6f} · <a href=\"{maps_url}\" target=\"_blank\">Google Maps</a>")
        except Exception:
            return "—"

    location_coords.short_description = _("Coordinates")

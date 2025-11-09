from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Try to use GeoDjango admin if available; fallback gracefully when GIS deps are missing
try:
    from django.contrib.gis.admin import OSMGeoAdmin  # type: ignore
except Exception:  # GeoDjango not available (e.g., missing GEOS/GDAL)
    class OSMGeoAdmin(admin.ModelAdmin):  # Fallback without map widget
        pass

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
        "_delivery_at"
    )
    search_fields = ("invoice__number", "recipient_expected",)
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
                "status", "delivery_at", "assigned_to", "invoice_address", "observations",
            ),
        }),
    )
    autocomplete_fields = ['invoice']
    readonly_fields = ["created_at", "delivery_at", "invoice_details", "invoice_address"]

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
    fields = ["image",]


@admin.register(ProofOfDelivery)
class ProofOfDeliveryAdmin(OSMGeoAdmin):
    list_display = ("id", "delivery", "received_by_name", "signed_at_server")
    search_fields = ("delivery__invoice__number", "received_by_name")
    list_filter = ("signed_at_server",)
    readonly_fields = ["signed_at_server", "created_at", "delivery_assigned_to"]
    fields = [
        "delivery",
        "delivery_assigned_to",
        "received_by_name",
        "received_by_document",
        "signed_at",
        "signed_at_server",
        "location",
        "signature_image",
        "meta",
    ]
    inlines = [ProofOfDeliveryPhotoInline]
    default_lon = -47.8825
    default_lat = -15.7942
    default_zoom = 4

    def delivery_assigned_to(self, obj):
        if not obj or not getattr(obj, "delivery_id", None):
            return "—"
        user = getattr(obj.delivery, "assigned_to", None)
        return str(user) if user else "—"
    delivery_assigned_to.short_description = _("Assigned to")

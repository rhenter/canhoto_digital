from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet

app_name = 'invoice'

router = DefaultRouter()
router.register(r"invoices", InvoiceViewSet, basename="invoice")
urlpatterns = router.urls

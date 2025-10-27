from rest_framework.routers import DefaultRouter
from .views import DeliveryViewSet, ProofOfDeliveryViewSet

app_name = 'delivery'


router = DefaultRouter()
router.register(r"deliveries", DeliveryViewSet, basename="delivery")
router.register(r"pods", ProofOfDeliveryViewSet, basename="pod")
urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet

app_name = 'company'

router = DefaultRouter()
router.register(r"companies", CompanyViewSet, basename="company")
urlpatterns = router.urls

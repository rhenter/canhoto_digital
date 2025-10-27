from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

app_name = 'api-user'

router.register(r'users', views.UserViewSet, basename='users')

urlpatterns = router.urls

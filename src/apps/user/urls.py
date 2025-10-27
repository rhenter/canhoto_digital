from rest_framework.routers import DefaultRouter

from . import views

app_name = 'user'

router = DefaultRouter()

router.register(r'users', views.UserViewSet, basename='users')

urlpatterns = router.urls

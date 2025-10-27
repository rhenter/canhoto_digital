from django.urls import path
from rest_framework.routers import DefaultRouter
from .views.http_status import page_not_found, unauthorized_access

from . import views

app_name = 'core'

router = DefaultRouter()

router.register(r'terms-of-service', views.TermsOfServiceViewSet, basename='terms-of-service')

urlpatterns = [
    path('', views.CustomLoginView.as_view(), name="login"),

    # Error Pages
    path('401/', unauthorized_access, name='unauthorized_access'),
    path('404/', page_not_found, name='page_not_found'),
]

urlpatterns += router.urls

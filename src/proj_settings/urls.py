from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.views import CustomLoginView, HealthCheckView, CustomTokenObtainPairView
from proj_settings.schema import get_schema_view, CustomOpenAPISchemaGenerator
from .admin_custom import admin_site, autodiscover_and_register

# Ensure all admin modules are discovered and registered
autodiscover_and_register()

extras = {
    "x-logo": {
        "url": "/static/img/logo.png",
        "altText": f"{settings.APP_NAME} API"
    }
}

schema_view = get_schema_view(
    openapi.Info(
        title=settings.APP_NAME,
        default_version=settings.APP_VERSION or 'v1',
        description=f"Backend API from {settings.APP_NAME}",
        terms_of_service=f"{settings.WEBSITE}/terms-of-service/",
        contact=openapi.Contact(email=settings.EMAIL_ADMIN),
        license=openapi.License(name="BSD License"),
        **extras
    ),
    public=True,
    # authentication_classes=(SessionAuthentication,),
    permission_classes=(permissions.AllowAny,),
    generator_class=CustomOpenAPISchemaGenerator
)

urlpatterns = [
    path('', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc-base'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        html_email_template_name='registration/password_reset_email.html',
    ), name='password_reset'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.logout_then_login, name='logout'),
    path('healthcheck/', HealthCheckView.as_view(), name="health_check"),
]

admin_patterns = i18n_patterns(
    path('doc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('admin/clearcache/', include('clearcache.urls')),
    path('admin/', admin_site.urls),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
)

api_urlpatterns = [
    path("v1/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/core/", include("apps.core.routes", namespace='core')),
    path("v1/delivery/", include("apps.delivery.urls", namespace='delivery')),
    path("v1/company/", include("apps.company.urls", namespace='company')),
    path("v1/invoice/", include("apps.invoice.urls", namespace='invoice')),
    path("v1/user/", include("apps.user.urls", namespace='user')),
]

urlpatterns.extend(admin_patterns)
urlpatterns.extend(api_urlpatterns)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

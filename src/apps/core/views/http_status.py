from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def unauthorized_access(request):
    template_data = {
        'code': 401,
        'message': _("Access Denied")
    }
    return render(request, "http_error.html", template_data, status=401)


def page_not_found(request, exception):
    template_data = {
        'code': 404,
        'message': _("Page Not Found")
    }
    return render(request, "http_error.html", template_data, status=404)

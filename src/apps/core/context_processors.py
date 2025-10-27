from django.conf import settings


def environment_info(request):
    """
    Return the current Environment info
    """
    return {
        'settings': settings,
    }

from django import template

register = template.Library()


@register.filter
def has_add_permission(models):
    """
    Check if any model in the list has add permission (add_url is not None/empty)
    """
    if not models:
        return False

    for model in models:
        if model.get('add_url'):
            return True

    return False

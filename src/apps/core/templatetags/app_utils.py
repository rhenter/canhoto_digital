from django import template

register = template.Library()


@register.filter(name='reverse_slugify')
def reverse_slugify(value):
    return ' '.join(value.split('_'))

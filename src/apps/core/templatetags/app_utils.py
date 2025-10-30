from datetime import date, datetime, timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name='reverse_slugify')
def reverse_slugify(value):
    return ' '.join(value.split('_'))


@register.filter(expects_localtime=True)
def calculate_age(value):
    days_of_year = 365.2425
    return (date.today() - value) // timedelta(days=days_of_year)


@register.filter(name='zip')
def zip_lists(a, b):
    return zip(a, b)


@register.filter(expects_localtime=True)
def time_elapsed(value):
    now = timezone.now()
    if not isinstance(value, str) and not isinstance(value, datetime):
        return value
    elif not isinstance(value, datetime):
        value = datetime.fromisoformat(value)

    delta = now - value
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 24:
        return f'{delta.days} dias'
    elif hours == 0:
        return f'{int(minutes)} mins'
    return '{:02}:{:02} horas'.format(int(hours), int(minutes))


@register.filter(expects_localtime=True)
def iso_to_datetime(value):
    if not value:
        return ''
    return datetime.fromisoformat(value)


@register.filter(expects_localtime=True)
def us_date_to_datetime(value):
    if not value:
        return ''
    return datetime.strptime(value, '%d/%m/%Y')


@register.filter(name='phone')
def phone_mask(item, mask="({}) {}-{}"):
    """ return (00) 00000-0000 or (00) 0000-0000  """
    if item and len(item) >= 11:
        return mask.format(
            item[0:2],
            item[2:7],
            item[7:11]
        )
    elif item:
        return mask.format(
            item[0:2],
            item[2:6],
            item[6:10]
        )


@register.filter(name='cpf')
def cpf_mask(item, mask="{}.{}.{}-{}"):
    """ return 000.000.000-00 """
    if item:
        return mask.format(
            item[0:3],
            item[3:6],
            item[6:9],
            item[9:11]
        )
    else:
        return None


@register.filter(name='rg')
def rg_mask(item, mask="{}.{}.{}-{}", other_mask="{}.{}.{}"):
    """
    return 00.000.000-0 or 0.000.000
    in this case I was have to create another mask to work with in both objects
    """
    if item and len(item) >= 8:
        return mask.format(
            item[0:2],
            item[2:5],
            item[5:8],
            item[8:9]
        )
    else:
        return other_mask.format(
            item[0:1],
            item[1:4],
            item[4:7]
        )


@register.filter(name='cnpj')
def cnpj_mask(item, mask="{}.{}.{}/{}-{}"):
    """ return 00.000.000/0000-00 """
    if item:
        return mask.format(
            item[0:2],
            item[2:5],
            item[5:8],
            item[8:12],
            item[12:14]
        )
    else:
        return None


@register.filter(name='cep')
def cep_mask(item, mask="{}-{}"):
    """ Return 00000-000 """
    if item:
        return mask.format(
            item[0:5],
            item[5:8]
        )
    else:
        return None


@register.simple_tag
def enterprise_logo_url(val=None):
    return f'images/logo_{val}.png'.lower()


@register.filter(name='get_coordinates')
def get_coordinates(value, key):
    aux = value.split(" ")
    return [aux[1].replace("(", ""), aux[2].replace(")", "")]

import codecs
import datetime
import gzip
import io
import json
import math
import os
import re
import uuid
from decimal import Decimal
from json import dumps
from typing import Optional, List, Any
from urllib.parse import (parse_qsl, ParseResult, unquote, urlencode, urlparse)

import pytz
from django.conf import settings
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django_models.utils import remove_special_characters
from unipath import Path

BASE_DIR = Path(__file__).ancestor(3)


def sqlalchemy_url_with_psycopg(url: str) -> str:
    try:
        import psycopg
        if "postgresql+psycopg://" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    except ImportError:
        pass
    return url


def capitalize(text, use_spaces=False):
    if '_' in text:
        words = text.split('_')
    else:
        words = [text]
    base_join = ''
    if use_spaces:
        base_join = ' '
    return base_join.join([word.title() for word in words])


def calculate_duration(start_time, end_time, verbose=True):
    run_time = end_time - start_time
    minutes = 0
    seconds = run_time
    if run_time > 60:
        minutes = round(int(seconds / 60))
        seconds = round(int(seconds % 60))

    if verbose:
        duration = f"{round(seconds)} secs"
        if minutes:
            duration = f"{round(minutes)} min and {duration}"
    else:
        duration = (
            f'{minutes}" '
            f'{round(seconds)}'
            "'"
        )
    return duration


def calculate_percentage(total, partial):
    return round((partial / total) * 100, 1)


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def convert_to_bool_if_possible(val):
    if not isinstance(val, str):
        return val

    if val.lower() == 'true':
        return True
    elif val.lower() == 'false':
        return False
    return val


def remove_html(raw_html):
    pattern = re.compile('<.*?>')
    return re.sub(pattern, '', raw_html)


def clean_filename(filename):
    fragment_filename = filename.split('.')
    name = '_'.join(remove_special_characters(
        ''.join(fragment_filename[:-1])).split()).lower()
    ext = fragment_filename[-1]
    return '{}.{}'.format(name, ext)


def get_version():
    current_version = ''
    changes = os.path.join(BASE_DIR, "CHANGES.rst")
    pattern = r'^(?P<version>[0-9]+.[0-9]+(.[0-9]+)?)'
    with codecs.open(changes, encoding='utf-8') as changes:
        for line in changes:
            match = re.match(pattern, line)
            if match:
                current_version = match.group("version")
                break
    return current_version or '0.1.0'


def upload_to(instance, filename, document_type='image'):
    folder = type(instance).__name__.lower()

    root_path = settings.MODEL_STORAGE_ROOT.get(
        folder, '{}s/'.format(document_type))
    filename = clean_filename(filename)

    return os.path.join(*[
        root_path,
        folder,
        str(instance.id),
        filename
    ])

def only_digits(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\D+", "", value)

def certificates_upload_path(instance, filename):
    base_path = settings.CERTIFICATES_STORAGE_ROOT
    if '/' in filename:
        filename = filename.split('/')[-1]

    full_path = os.path.join(*[
        "company",
        base_path,
        only_digits(instance.cnpj),
        f"{filename}"
    ])
    return full_path


def pod_signature_upload_path(instance, filename):
    base_path = settings.POD_SIGNATURES_STORAGE_ROOT
    invoice_number = instance.invoice_number.replace('/', '-')

    if '/' in filename:
        filename = filename.split('/')[-1]

    full_path = os.path.join(*[
        "pod",
        f"{invoice_number}",
        base_path,
        f"{filename}"
    ])
    return full_path


def pod_photo_upload_path(instance, filename):
    base_path = settings.POD_PHOTO_STORAGE_ROOT
    invoice_number = instance.pod.invoice_number.replace('/', '-')

    if '/' in filename:
        filename = filename.split('/')[-1]

    full_path = os.path.join(*[
        "pod",
        f"{invoice_number}",
        base_path,
        f"{filename}"
    ])
    return full_path

def image_upload_path(instance, filename):
    return upload_to(instance, filename, document_type='image')


def is_email(text):
    pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return bool(re.search(pattern, text))


def get_verbose_timedelta(days):
    years = 0
    months = int(days / 30)
    if months > 12:
        years = int(months / 12)
        months = months - (years * 12)
    return _("{} years and {} months").format(years, months)


def clean_url(url):
    url = unquote(url)
    # Extracting url info
    parsed_url = urlparse(url)
    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query
    # Converting URL arguments to dict
    parsed_get_args = dict(parse_qsl(get_args))
    # Merging URL arguments dict with new params
    parsed_get_args.pop('page', '')

    parsed_get_args.update(
        {k: dumps(v) for k, v in parsed_get_args.items()
         if isinstance(v, (bool, dict))}
    )

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)
    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme, parsed_url.netloc, parsed_url.path,
        parsed_url.params, encoded_get_args, parsed_url.fragment
    ).geturl()

    return new_url


def slugify(word, is_remove_special_characters=True):
    if is_remove_special_characters:
        return '_'.join(remove_special_characters(''.join(word)).split()).lower()
    return '_'.join(word.split()).lower()


def value_to_cents(value):
    return str(int(value * 100))


def cost_format(cost):
    if cost == 'N/A' or not cost:
        return cost
    return number_format(round(Decimal(cost), 2))


def time_in_range(hour_block, timestamp):
    """Return true if x is in the range [start, end]"""
    if hour_block == '20+':
        _start = 20
        _end = 0
    else:
        _start, _end = hour_block.split('-')

    start = datetime.time(int(_start), 0, 0)
    end = datetime.time(int(_end), 0, 0)
    if start <= end:
        return start <= timestamp <= end
    else:
        return start <= timestamp or timestamp <= end


def clean_fields(data, extra_fields=[], code_field=False, keep_fields=False):
    if not keep_fields:
        to_remove = ['id', 'created_at', 'updated_at'] + extra_fields
        if not code_field:
            to_remove.append('code')
    else:
        to_remove = [key for key in data.keys() if key not in extra_fields]

    for key in to_remove:
        data.pop(key, '')
    return data


def create_new_dict_from_keys(data_dict, keys):
    return {key: data_dict.get(key, '') for key in keys}


def get_name_from_slug(slug, delimiter='_'):
    return ' '.join([word.title() for word in slug.split(delimiter)])


def get_all_timezones_choices():
    return tuple((tz, tz) for tz in pytz.all_timezones)


def apply_compression(content, compress_level=9):
    gz_body = io.BytesIO()
    gz = gzip.GzipFile(None, 'wb', compress_level, gz_body)
    gz.write(content)
    gz.close()
    return gz_body


def compress_json(content: bytes, json_dump: bool = True):
    if not json_dump:
        serialized_data = json.dumps(content, default=str).encode('utf-8')
    else:
        serialized_data = content
    gz_content = apply_compression(serialized_data)
    gz_content.seek(0)

    return gz_content.read()


def decompress_json(compress_content: bytes) -> Any:
    content_decompress = gzip.decompress(compress_content)
    return json.loads(content_decompress)


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def remove_substring(a_string: str, list_to_replace: Optional[List[str]] = None) -> str:
    if list_to_replace:
        for r in list_to_replace:
            a_string = a_string.replace(r, '')
    return a_string

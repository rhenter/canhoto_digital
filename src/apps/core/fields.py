import gzip
import io
import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.text import compress_string
from rest_framework import serializers, ISO_8601


class CustomDateTimeField(serializers.DateTimeField):

    def to_representation(self, value):
        if not value:
            return None

        output_format = getattr(self, 'format', settings.DATETIME_FORMAT)

        if output_format is None or isinstance(value, str):
            return value

        value = self.enforce_timezone(value)

        if output_format.lower() == ISO_8601:
            value = value.isoformat()
            return value
        return value.strftime(output_format)


class CompressedBinaryField(models.BinaryField):
    compress = compress_string

    @staticmethod
    def uncompress(s):
        zbuf = io.BytesIO(s)
        zfile = gzip.GzipFile(fileobj=zbuf)
        ret = zfile.read()
        zfile.close()
        return ret

    def get_db_prep_save(self, value, connection=None, prepared=False):
        if value is not None and prepared is False:
            value = CompressedBinaryField.compress(value)
        return models.BinaryField.get_db_prep_save(self, value, connection)

    def is_binary(self, value):
        return value and (type(value) == bytes or isinstance(value, memoryview))

    def _get_val_from_obj(self, obj):
        val = obj and getattr(obj, self.attname)
        if self.is_binary(val):
            return CompressedBinaryField.uncompress(val)
        if val is None:
            return self.get_default()
        return val

    def post_init(self, instance=None, **kwargs):
        value = self._get_val_from_obj(instance)
        setattr(instance, self.attname, value)

    def contribute_to_class(self, cls, name, private_only=False):
        super(CompressedBinaryField, self).contribute_to_class(cls, name)
        models.signals.post_init.connect(self.post_init, sender=cls)

    def get_internal_type(self):
        return 'BinaryField'


class CompressedJSONField(CompressedBinaryField):
    encoder = DjangoJSONEncoder

    def __init__(self, *args, **kwargs):
        self.encoder = kwargs.pop('encoder', DjangoJSONEncoder)
        super().__init__(*args, **kwargs)

    def get_db_prep_save(self, value, connection=None, prepared=False):
        if value is not None and prepared is False:
            value = json.dumps(value, cls=self.encoder).encode('utf-8')
        return super().get_db_prep_save(value, connection, prepared)

    def _get_val_from_obj(self, obj):
        if obj:
            val = super()._get_val_from_obj(obj)
            if self.is_binary(val):
                return json.loads(val.decode('utf-8'))
            return val
        else:
            return self.get_default()

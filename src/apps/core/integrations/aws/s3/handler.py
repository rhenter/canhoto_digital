import logging
import pickle
from functools import cached_property
from typing import Any

from botocore.client import BaseClient
from botocore.config import Config
from django.conf import settings

from apps.core.decorators import timer
from proj_settings.utils import apply_compression
from ..base import AwsBase

logger = logging.getLogger(__name__)


class AwsS3Handler(AwsBase):

    def __init__(self, debug: bool = False, **kwargs):
        super().__init__(debug, **kwargs)
        self.bucket_name = (
                kwargs.get("bucket_name", "") or settings.AWS_STORAGE_BUCKET_NAME
        )

    def __repr__(self):
        return f'<AwsHandler: {self.aws_access_key_id}>'

    def __str__(self):
        return f'AwsHandler -> {self.aws_access_key_id}'

    @cached_property
    def s3_client(self) -> BaseClient:
        return self.boto_session.client('s3', config=Config(signature_version=settings.AWS_S3_SIGNATURE_VERSION))

    def _get_s3_bucket(self) -> Any:
        if not self.bucket_name:
            raise Exception('AWS S3 Bucket is required.')

        s3_resource = self.boto_session.resource(
            's3',
            config=Config(signature_version=settings.AWS_S3_SIGNATURE_VERSION)
        )
        return s3_resource.Bucket(f"{self.bucket_name}")

    def get_url_from_s3(self, key: str, expires_in: int = 7200) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            ExpiresIn=expires_in,
            Params={"Bucket": self.bucket_name, "Key": key},
            HttpMethod="GET",
        )

    def get_download_url_from_s3(self, key: str, expires_in: int = 7200) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            ExpiresIn=expires_in,
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                'ResponseContentType': 'application/force-download'
            },
            HttpMethod="GET",
        )

    @timer
    def write_dataframe_to_s3(self, obj: Any, key: str, as_compressed: bool = True) -> Any:
        bucket = self._get_s3_bucket()
        serialized_data = pickle.dumps(obj)

        if not as_compressed:
            response = bucket.Object(key=key).put(
                Body=obj.getvalue()
            )
        else:
            gz_body = apply_compression(serialized_data)
            response = bucket.Object(key=key).put(
                ContentType='text/plain',
                ContentEncoding='gzip',
                Body=gz_body.getvalue()
            )
        if self.debug:
            logger.debug(f'S3 Response: {response}')
        return response

    @timer
    def write_json_to_s3(self, obj: Any, key: str) -> Any:
        bucket = self._get_s3_bucket()
        response = bucket.Object(key=key).put(
            Body=obj
        )

        if self.debug:
            logger.debug(f'S3 Response: {response}')
        return response

import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class AwsBase:
    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug
        self.aws_config = kwargs.get("aws_config", {}) or settings.AWS_CONFIG
        self.aws_access_key_id = self.aws_config.get("aws_access_key_id", "")
        if not self.aws_access_key_id:
            raise Exception("AWS Credentials are required.")

        self.boto_session = boto3.Session(**self.aws_config)

    def __repr__(self):
        class_name = type(self).__name__
        return f"<{class_name}: {str(self)}>"

    def __str__(self):
        return self.aws_access_key_id

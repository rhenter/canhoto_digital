import json
import logging
from functools import cached_property
from typing import Any, Dict

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ..base import AwsBase

logger = logging.getLogger(__name__)


class AwsSnsHandler(AwsBase):
    @cached_property
    def sns_client(self) -> BaseClient:
        return self.boto_session.client("sns")

    def create_sns_topic(self, topic_name):
        topic = self.sns_client.create_topic(Name=topic_name)
        if self.debug:
            logger.debug(f"Topic Response: {topic}")
        if not topic:
            return ""
        return topic["TopicArn"]

    def get_all_topics(self):
        all_topics = []
        response = self.sns_client.list_topics()

        all_topics.extend(response["Topics"])

        # Keep paginating if there is a NextToken in the response
        while "NextToken" in response:
            response = self.sns_client.list_topics(NextToken=response["NextToken"])
            all_topics.extend(response["Topics"])

        return all_topics

    def get_topic_arn(self, topic_name) -> str:
        topics = self.get_all_topics()
        topic = next(filter(lambda n: topic_name in n.get("TopicArn"), topics), None)
        if not topic:
            return ""
        return topic["TopicArn"]

    def publish_sns_message(self, topic_arn: Any, message: Dict):
        try:
            str_message = json.dumps({"default": json.dumps(message)})
            logger.debug(f"Message size: {len(str_message.encode('utf-8'))}")
            response = self.sns_client.publish(
                TopicArn=topic_arn, Message=str_message, MessageStructure="json"
            )
            message_id = response["MessageId"]
            logger.debug(
                f"Published message with message {message_id} to topic {topic_arn}."
            )
        except ClientError as exc:
            logger.exception(
                f"Couldn't publish message to topic {topic_arn}. Error: {str(exc)}"
            )
            raise exc

        return response

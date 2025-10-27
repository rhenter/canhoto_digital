import json
import logging
from functools import cached_property

from botocore.client import BaseClient

from ..sns import AwsSnsHandler

logger = logging.getLogger(__name__)


class AwsSqsHandler(AwsSnsHandler):

    @cached_property
    def sqs_client(self) -> BaseClient:
        return self.boto_session.client("sqs")

    @cached_property
    def sqs_resource(self) -> BaseClient:
        return self.boto_session.resource("sqs")

    def count_queue_messages(self, queue_name):
        queue = self.get_sqs_queue(queue_name)
        return queue.attributes.get('ApproximateNumberOfMessages')

    def create_sqs_queue(self, queue_name):
        queue = self.sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                "VisibilityTimeout": str(300),
            },
        )
        queue_url = queue["QueueUrl"]
        return queue_url

    def create_sqs_subscription(self, topic_arn, queue_arn):
        subscription = self.sns_client.subscribe(
            TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_arn
        )
        if self.debug:
            logger.debug(f"subscription Response: {subscription}")
        return subscription

    def get_sqs_queue(self, queue_name):
        return self.sqs_resource.get_queue_by_name(QueueName=queue_name)

    def get_sqs_queue_arn(self, queue_url):
        queue_arn = self.sqs_client.get_queue_attributes(
            QueueUrl=queue_url, AttributeNames=["All"]
        )["Attributes"]["QueueArn"]
        return queue_arn

    def get_sqs_queue_url(self, queue_name):
        queue_urls = self.sqs_client.list_queues()["QueueUrls"]
        queue_url = next(filter(lambda n: queue_name in n, queue_urls), None)
        return queue_url

    def purge_queue(self, queue_name):
        queue_url = self.get_sqs_queue_url(queue_name)
        response = self.sqs_client.purge_queue(QueueUrl=queue_url)
        return response

    def read_from_sqs_queue(self, queue_name):
        queue_url = self.get_sqs_queue_url(queue_name)
        response = self.sqs_client.receive_message(
            QueueUrl=queue_url,
            AttributeNames=["All"],
            MessageAttributeNames=["All"],
            WaitTimeSeconds=20,
        )
        if not len(response["Messages"]):
            return []

        return [
            json.loads(json.loads(message["Body"])["Message"])
            for message in response["Messages"]
        ]

    def set_sqs_queue_permissions(self, queue_arn, queue_url, topic_arn):
        policy = {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "sqs:SendMessage",
                    "Resource": queue_arn,
                    "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
                }
            ],
        }

        queue_attributes = self.sqs_client.set_queue_attributes(
            QueueUrl=queue_url, Attributes={"Policy": json.dumps(policy)}
        )
        if self.debug:
            logger.debug(
                f"SQS Response: \n"
                f"Queue: {queue_url} \n"
                f"ARN: {queue_arn} \n"
                f"Attributes: {queue_attributes} \n"
            )

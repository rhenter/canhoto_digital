import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.integrations.aws.amazon_mq import AmazonMqHandler


class Command(BaseCommand):
    help = 'Check Celery queues (AmazonMQ)'

    def add_arguments(self, parser):
        # Optional argument
        parser.add_argument('-ad', '--all_details', action='store_true', help='Details of all Queues')
        parser.add_argument('-p', '--purge', type=str, help='Purge queue messages')

    def handle(self, *args, **options):
        all_details = options.get('all_details')
        purge = options.get('purge')

        self.stdout.write(f'Checking Celery queues from {settings.ENV.title()}')

        mq_handler = AmazonMqHandler()
        self.stdout.write('\n\n')
        self.stdout.write('-' * 79)
        response = 'Invalid Option. Need to choose one.'

        if all_details:
            queues = mq_handler.get_queue_details()

            # Print table header
            self.stdout.write(f"{'Queue Name':<30} {'Consumers':<10} {'Messages':<10}")
            self.stdout.write('-' * 52)

            # Print queue details in table format
            for queue_info in queues:
                queue_name = queue_info.get('queue', 'N/A')
                consumer_count = queue_info.get('consumer_count', 0)
                message_count = queue_info.get('message_count', 0)
                self.stdout.write(f"{queue_name:<32} {consumer_count:<10} {message_count:<10}")

            response = f'Found {len(queues)} queues directly from Amazon MQ'

        if purge:
            response = mq_handler.purge_messages(queue_name=purge)

        self.stdout.write('-' * 79)
        self.stdout.write(f'\t {response} \n')

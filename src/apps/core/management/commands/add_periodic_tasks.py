import inspect
import json
from typing import Dict

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

from ..data.tasks import periodic_tasks_data


class PeriodicTaskCreator:

    def __init__(self, task_data: dict) -> None:
        for key in task_data:
            value = task_data.get(key)
            if key == 'interval_id':
                key = 'interval'
                value = self._get_or_create_interval(value)
            elif key == 'crontab_id':
                key = 'crontab'
                value = self._get_or_create_crontab(value)
            elif key in ['args', 'kwargs']:
                value = json.dumps(value)
            setattr(self, key, value)

    def _get_or_create_interval(self, interval_data: dict) -> IntervalSchedule:
        interval_data['period'] = getattr(IntervalSchedule, interval_data['period'].upper())
        interval, _ = IntervalSchedule.objects.get_or_create(**interval_data)
        return interval

    def _get_or_create_crontab(self, crontab_data: dict) -> CrontabSchedule:
        crontab, _ = CrontabSchedule.objects.get_or_create(**crontab_data)
        return crontab

    def serialize(self) -> Dict:
        data = {}
        for key, value in inspect.getmembers(self):
            # Ignores anything starting with underscore (that is, private and protected attributes)
            if not key.startswith("_"):
                if not inspect.ismethod(value):
                    data[key] = value
        return data

    def create_task(self) -> bool:
        serialized_data = self.serialize()
        try:
            PeriodicTask.objects.get_or_create(**serialized_data)
        except ValidationError:
            pass

        return True


class Command(BaseCommand):
    help = 'Adding Celery Beat Periodic Tasks'

    def add_arguments(self, parser):
        # Optional argument
        parser.add_argument('-r', '--recreate', action='store_true', help='Recreate all Periodic Tasks')

    def handle(self, *args, **options):
        recreate = options.get('recreate')
        self.stdout.write('Adding Celery Beat Periodic Tasks')

        if recreate:
            self.stdout.write('\nDeleting all Current Periodic Tasks.\n\n')
            PeriodicTask.objects.all().delete()
        self.stdout.write('-' * 79)
        self.stdout.write('Periodic Tasks')
        self.stdout.write('-' * 79)
        for task_data in reversed(periodic_tasks_data):
            task_creator = PeriodicTaskCreator(task_data)
            task_creator.create_task()
            self.stdout.write(f'{task_data["name"]} task created.\n')
        self.stdout.write('\nAll Periodic test created.\n')

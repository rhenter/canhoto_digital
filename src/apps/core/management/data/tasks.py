import pytz

periodic_tasks_data = [
    {
        'name': 'clear_celery_task_logs',
        'task': 'clear_celery_task_logs',
        'crontab_id': {
            'minute': '1',
            'hour': '0',
            'day_of_week': '*',
            'day_of_month': '*',
            'month_of_year': '*',
            'timezone': pytz.timezone("UTC")
        },
        'args': [],
        'kwargs': {}
    },
]

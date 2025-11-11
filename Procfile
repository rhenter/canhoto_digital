web: gunicorn proj_settings.wsgi:application --chdir src --log-file -
release: python src/manage.py migrate

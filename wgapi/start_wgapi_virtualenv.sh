#!/bin/bash

echo "Activating virtual environment..."
source /path/to/your/project/venv/bin/activate

echo "Starting wgapi with Gunicorn and Celery..."
cd /path/to/your/project

# Start Gunicorn server
echo "Starting Gunicorn..."
gunicorn wgapi.wsgi:application --bind 0.0.0.0:8000 --workers 3 &

# Start Celery worker
echo "Starting Celery Worker..."
celery -A wgapi worker --loglevel=info &

# Start Celery beat (Для отложенных задач)
echo "Starting Celery Beat..."
celery -A wgapi beat --loglevel=info &

# Ожидаем выход
wait -n

# Выходит с указанием того, что не так
exit $?

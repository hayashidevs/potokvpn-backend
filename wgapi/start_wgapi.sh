#!/bin/bash

echo "Starting wgapi with Gunicorn and Celery..."

# Navigate to your Django project directory
cd /mnt/hgfs/VPN/wgapi

# Check for gunicorn installation
if ! command -v gunicorn &> /dev/null
then
    echo "Gunicorn could not be found, please install it first."
    exit 1
fi

# Start Gunicorn server
echo "Starting Gunicorn..."
gunicorn wgapi.wsgi:application --bind 0.0.0.0:8000 --workers 3 &

# Check for celery installation
if ! command -v celery &> /dev/null
then
    echo "Celery could not be found, please install it first."
    exit 1
fi

# Start Celery worker
echo "Starting Celery Worker..."
celery -A wgapi worker --loglevel=info &

# Start Celery beat (if you are using scheduled tasks)
echo "Starting Celery Beat..."
celery -A wgapi beat --loglevel=info &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?

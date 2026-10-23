#!/bin/bash
set -e

echo "Starting deployment sequence..."

# 1. Jalankan migrasi database
echo "Running database migrations..."
python manage.py migrate --noinput

# 2. Jalankan collectstatic (Wajib untuk WhiteNoise)
echo "Collecting static files locally..."
python manage.py collectstatic --noinput

# 3. Jalankan server Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn inside.wsgi:application --bind 0.0.0.0:$PORT
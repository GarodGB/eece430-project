#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "Preparing synthetic demo data..."
    python manage.py seed_data
fi

echo "Starting PharmaLink..."
exec "$@"
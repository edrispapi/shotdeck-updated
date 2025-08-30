#!/bin/sh
# مسیر: /home/mdk/Documents/shotdeck-main/search_service/entrypoint.sh
set -e

echo "Waiting for Elasticsearch to be ready..."
while ! nc -z elasticsearch 9200; do
  sleep 1
done
echo "Elasticsearch is ready."

echo "Waiting for Kafka to be ready..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "Kafka is ready."

# --- تغییر کلیدی: اضافه کردن دستور migrate ---
# این دستور جداول داخلی جنگو (مانند auth, sessions, admin) را در db.sqlite3 ایجاد می‌کند.
echo "Applying database migrations for search_service..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# اجرای Kafka consumer در پس‌زمینه
echo "Starting Kafka consumer in the background..."
python manage.py run_kafka_consumer &

# اجرای سرور جنگو در پیش‌زمینه
echo "Starting search_service server..."
exec python manage.py runserver 0.0.0.0:8000
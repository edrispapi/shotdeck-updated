# مسیر: search_service/Dockerfile
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends netcat-traditional && rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# --- تغییر کلیدی: حذف مسیر اضافی ---
# چون context ما همان پوشه search_service است، فقط نام فایل کافی است.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# دستور پیش‌فرض برای اجرای کانتینر
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# مسیر: deck_service/Dockerfile
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends netcat-traditional && rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# --- تغییر کلیدی: کپی کردن entrypoint به یک مسیر امن ---
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# دستور پیش‌فرض برای اجرای کانتینر
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
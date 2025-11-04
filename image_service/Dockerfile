FROM python:3.11-slim
WORKDIR /service

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-traditional curl postgresql-client build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]

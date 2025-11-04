#!/bin/bash

echo "Testing Image Service API..."
echo ""

URLS=(
    "http://localhost:8000/api/images/?limit=1"
    "http://127.0.0.1:8000/api/images/?limit=1"
    "http://image_service:8000/api/images/?limit=1"
)

for url in "${URLS[@]}"; do
    echo "Testing: $url"
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ $response -eq 200 ]; then
        echo "✅ SUCCESS - $url is working!"
        echo "Use: python manage.py analyze_from_service --api-url ${url%/images/*}"
        break
    else
        echo "❌ Failed (HTTP $response)"
    fi
    echo ""
done

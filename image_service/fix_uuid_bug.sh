echo "═══════════════════════════════════════════════"
echo "🔍 COMPLETE DIAGNOSTIC & FIX"
echo "═══════════════════════════════════════════════"

echo -e "\n1️⃣ Checking current error..."
curl -s http://localhost:51009/api/images/ | jq -r '.error // "No error field"'

echo -e "\n2️⃣ Showing the bug (line 111)..."
docker exec -it image_service sed -n '109,113p' /service/apps/images/api/views.py

echo -e "\n3️⃣ Checking model field name..."
docker exec -it image_service python manage.py shell << 'PYEOF'
from apps.images.models import Image
fields = [f.name for f in Image._meta.fields if 'id' in f.name or 'uuid' in f.name]
print(f"Fields with 'id' or 'uuid': {fields}")
print(f"Primary key field: {Image._meta.pk.name}")
print(f"Primary key type: {Image._meta.pk.get_internal_type()}")
PYEOF

echo -e "\n4️⃣ Applying fix..."
docker exec -it image_service cp /service/apps/images/api/views.py{,.backup}
docker exec -it image_service sed -i "111s/'uuid'/'id'/" /service/apps/images/api/views.py
echo "✅ Changed 'uuid' to 'id' on line 111"

echo -e "\n5️⃣ Restarting service..."
docker compose restart image_service
sleep 8

echo -e "\n6️⃣ Testing fixed API..."
RESPONSE=$(curl -s http://localhost:51009/api/images/)
echo "$RESPONSE" | jq -r '.error // "✅ No error - API works!"'
echo "$RESPONSE" | jq -r '.count // 0' | xargs -I {} echo "   Found {} images"

echo -e "\n═══════════════════════════════════════════════"
echo "✅ DIAGNOSTIC COMPLETE"
echo "═══════════════════════════════════════════════"
#!/bin/bash

echo "═══════════════════════════════════════════════"
echo "✅ COMPLETE VERIFICATION"
echo "═══════════════════════════════════════════════"

echo -e "\n1️⃣ Database Schema:"
docker exec image-db psql -U postgres -d image_service_db -c "
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_name IN ('images_image', 'images_movie', 'images_tag', 'images_image_tags')
  AND column_name LIKE '%id%'
ORDER BY table_name, column_name;
" | grep -E "table_name|image|movie|tag" | head -20

echo -e "\n2️⃣ Data Counts:"
docker exec image-db psql -U postgres -d image_service_db -c "
SELECT 'Images' as table_name, COUNT(*) FROM images_image
UNION ALL SELECT 'Movies', COUNT(*) FROM images_movie
UNION ALL SELECT 'Tags', COUNT(*) FROM images_tag
UNION ALL SELECT 'Image-Tag Links', COUNT(*) FROM images_image_tags;
"

echo -e "\n3️⃣ Sample Image (UUID check):"
docker exec image-db psql -U postgres -d image_service_db -c "
SELECT 
    id,
    slug,
    LEFT(title, 40) as title,
    movie_id
FROM images_image 
LIMIT 2;
"

echo -e "\n4️⃣ API Response:"
API_RESPONSE=$(curl -s http://localhost:51009/api/images/)
echo "$API_RESPONSE" | jq '{
    success: .success // false,
    count: .count // 0,
    error: .error // null,
    first_image_id: .results[0].id // null,
    first_image_title: .results[0].title // null
}'

echo -e "\n5️⃣ API Filters Test:"
curl -s 'http://localhost:51009/api/images/?limit=5' | jq '{
    count: .count,
    returned: (.results | length),
    error: .error // null
}'

echo -e "\n═══════════════════════════════════════════════"
echo "✅ VERIFICATION COMPLETE"
echo "═══════════════════════════════════════════════"

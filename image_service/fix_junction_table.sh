#!/bin/bash

echo "═══════════════════════════════════════════════"
echo "🔧 FIXING JUNCTION TABLE TYPE MISMATCH"
echo "═══════════════════════════════════════════════"

echo -e "\n1️⃣ Checking junction table data..."
TAG_COUNT=$(docker exec image-db psql -U postgres -d image_service_db -t -c "SELECT COUNT(*) FROM images_image_tags;")
echo "   Tag associations: $TAG_COUNT"

if [ "$TAG_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: Junction table has data! Manual migration required."
    exit 1
fi

echo -e "\n2️⃣ Backing up old junction table..."
docker exec image-db psql -U postgres -d image_service_db -c "
CREATE TABLE IF NOT EXISTS images_image_tags_old AS SELECT * FROM images_image_tags;
"

echo -e "\n3️⃣ Dropping old junction table..."
docker exec image-db psql -U postgres -d image_service_db -c "
DROP TABLE IF EXISTS images_image_tags CASCADE;
"

echo -e "\n4️⃣ Recreating junction table with UUID..."
docker exec image-db psql -U postgres -d image_service_db << 'EOF'
CREATE TABLE images_image_tags (
    id SERIAL PRIMARY KEY,
    image_id UUID NOT NULL,
    tag_id BIGINT NOT NULL,
    CONSTRAINT images_image_tags_image_id_tag_id_key UNIQUE (image_id, tag_id),
    CONSTRAINT images_image_tags_image_id_fkey 
        FOREIGN KEY (image_id) REFERENCES images_image(id) ON DELETE CASCADE,
    CONSTRAINT images_image_tags_tag_id_fkey 
        FOREIGN KEY (tag_id) REFERENCES images_tag(id) ON DELETE CASCADE
);

CREATE INDEX images_image_tags_image_id_idx ON images_image_tags(image_id);
CREATE INDEX images_image_tags_tag_id_idx ON images_image_tags(tag_id);
EOF

echo -e "\n5️⃣ Verifying new structure..."
docker exec image-db psql -U postgres -d image_service_db -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'images_image_tags' 
ORDER BY ordinal_position;
"

echo -e "\n6️⃣ Faking Django migration state..."
docker exec -it image_service python manage.py migrate images --fake

echo -e "\n7️⃣ Restarting service..."
docker compose restart image_service
sleep 5

echo -e "\n8️⃣ Testing API..."
RESULT=$(curl -s http://localhost:51009/api/images/)
echo "$RESULT" | jq -r '.count // .error // "Unknown response"' | xargs -I {} echo "   Result: {}"

echo -e "\n═══════════════════════════════════════════════"
echo "✅ Junction table fix complete!"
echo "═══════════════════════════════════════════════"

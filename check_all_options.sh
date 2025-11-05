#!/bin/bash

DB_USER="postgres"
DB_NAME="image_service_db"

echo "======================================"
echo "DATABASE OPTION TABLES VERIFICATION"
echo "======================================"
echo ""

# 1. Connection test
echo "1️⃣  Testing connection..."
docker exec image-db psql -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Connected successfully"
else
    echo "❌ Connection failed"
    exit 1
fi
echo ""

# 2. Image count
echo "2️⃣  Total images in database:"
docker exec image-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM images_image;"
echo ""

# 3. Option tables count
echo "3️⃣  Option tables row counts:"
docker exec image-db psql -U $DB_USER -d $DB_NAME -c "
    SELECT 
        tablename,
        (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I', tablename), false, true, '')))[1]::text::int as row_count
    FROM pg_tables 
    WHERE tablename LIKE '%_options'
    ORDER BY tablename;
" 2>/dev/null

# Alternative simpler method
echo ""
echo "4️⃣  Sample values from key option tables:"
echo ""

tables=(
    "color_options"
    "time_of_day_options"
    "interior_exterior_options"
    "shot_type_options"
    "frame_size_options"
    "lighting_options"
    "composition_options"
    "aspect_ratio_options"
    "format_options"
    "lens_type_options"
    "media_type_options"
)

for table in "${tables[@]}"; do
    echo "--- $table ---"
    count=$(docker exec image-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM $table;")
    echo "Total: $count"
    echo "Values:"
    docker exec image-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT '  - ' || value FROM $table ORDER BY value;" | head -15
    echo ""
done

echo "5️⃣  Large option tables (people/equipment):"
echo ""

large_tables=(
    "director_options"
    "cinematographer_options"
    "camera_options"
    "lens_options"
    "editor_options"
    "production_designer_options"
)

for table in "${large_tables[@]}"; do
    count=$(docker exec image-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM $table;")
    echo "$table: $count rows"
    echo "Sample:"
    docker exec image-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT '  - ' || value FROM $table ORDER BY value LIMIT 5;"
    echo ""
done

echo "======================================"
echo "DATABASE CHECK COMPLETE"
echo "======================================"

#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "📊 METADATA COVERAGE REPORT"
echo "═══════════════════════════════════════════════════════"

# Get total
TOTAL=$(curl -s 'http://localhost:51009/api/images/' | jq -r '.count')
echo "Total Images: $TOTAL"

echo -e "\n📈 Field Coverage:"
echo "─────────────────────────────────────────────────────"

# Query database for coverage
docker exec image-db psql -U postgres -d image_service_db -t << 'SQL'
SELECT 
    LPAD(field, 25) || ' ' || 
    LPAD(filled::text, 5) || '/' || 
    LPAD(total::text, 5) || ' (' || 
    LPAD(ROUND(pct, 1)::text, 5) || '%)'
FROM (
    SELECT 'director' as field,
        COUNT(*) FILTER (WHERE director_id IS NOT NULL) as filled,
        COUNT(*) as total,
        100.0 * COUNT(*) FILTER (WHERE director_id IS NOT NULL) / COUNT(*) as pct
    FROM images_image
    UNION ALL
    SELECT 'cinematographer',
        COUNT(*) FILTER (WHERE cinematographer_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE cinematographer_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'color',
        COUNT(*) FILTER (WHERE color_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE color_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'shade',
        COUNT(*) FILTER (WHERE shade_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE shade_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'shot_type',
        COUNT(*) FILTER (WHERE shot_type_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE shot_type_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'lighting',
        COUNT(*) FILTER (WHERE lighting_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE lighting_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'camera',
        COUNT(*) FILTER (WHERE camera_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE camera_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'lens',
        COUNT(*) FILTER (WHERE lens_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE lens_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'aspect_ratio',
        COUNT(*) FILTER (WHERE aspect_ratio_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE aspect_ratio_id IS NOT NULL) / COUNT(*)
    FROM images_image
    UNION ALL
    SELECT 'interior_exterior',
        COUNT(*) FILTER (WHERE interior_exterior_id IS NOT NULL),
        COUNT(*),
        100.0 * COUNT(*) FILTER (WHERE interior_exterior_id IS NOT NULL) / COUNT(*)
    FROM images_image
) coverage
ORDER BY pct DESC;
SQL

echo "═══════════════════════════════════════════════════════"

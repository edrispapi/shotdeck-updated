#!/bin/bash

FILTER=$1

if [ -z "$FILTER" ]; then
    echo "Usage: ./list_filters.sh <filter_name>"
    echo ""
    echo "Available filters:"
    echo "  color, shot_type, lighting, director, cinematographer"
    echo "  time_of_day, interior_exterior, composition, etc."
    exit 1
fi

# Map filter names to API field names
case $FILTER in
    color)
        API_FIELD="color_value"
        ;;
    shot_type)
        API_FIELD="shot_type_value"
        ;;
    lighting)
        API_FIELD="lighting_value"
        ;;
    director)
        API_FIELD="director_value"
        ;;
    cinematographer)
        API_FIELD="cinematographer_value"
        ;;
    *)
        API_FIELD="${FILTER}_value"
        ;;
esac

echo "Available values for '$FILTER':"
curl -s "http://localhost:51009/api/images/?limit=100" | \
    jq -r ".results[] | .${API_FIELD} // empty" | \
    sort -u | \
    head -20

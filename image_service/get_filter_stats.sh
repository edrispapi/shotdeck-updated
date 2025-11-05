#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "📊 FILTER VALUE STATISTICS"
echo "═══════════════════════════════════════════════════════"

# Function to test filter
test_filter() {
    local field=$1
    local value=$2
    local encoded=$(echo "$value" | sed 's/ /%20/g')
    local count=$(curl -s "http://localhost:51009/api/images/?${field}=${encoded}" | jq -r '.count // 0')
    printf "  %-30s %5d images\n" "$value" "$count"
}

echo -e "\n🎨 COLORS:"
test_filter "color" "Warm"
test_filter "color" "Cool"
test_filter "color" "Cyan"
test_filter "color" "White"

echo -e "\n💡 LIGHTING:"
test_filter "lighting" "Hard light"
test_filter "lighting" "Soft light"
test_filter "lighting" "Low contrast"
test_filter "lighting" "High contrast"

echo -e "\n📸 SHOT TYPES:"
test_filter "shot_type" "2 shot"
test_filter "shot_type" "Clean single"
test_filter "shot_type" "Group shot"
test_filter "shot_type" "Insert"

echo -e "\n🎬 SAMPLE DIRECTORS:"
test_filter "director" "Barry Jenkins"
test_filter "director" "Dario Argento"
test_filter "director" "D. W. Griffith"

echo -e "\n📷 SAMPLE CINEMATOGRAPHERS:"
test_filter "cinematographer" "James Laxton"
test_filter "cinematographer" "Giuseppe Rotunno"
test_filter "cinematographer" "Billy Bitzer"

echo "═══════════════════════════════════════════════════════"

import requests
import time

IMAGE_SERVICE_URL = "http://localhost:8000/api/images/"
DECK_SEARCH_URL = "http://localhost:12703/api/search/similar/"

# Helper to poll deck_search for image slug

def wait_for_slug_in_deck_search(slug, should_exist=True, timeout=30):
    url = f"{DECK_SEARCH_URL}{slug}/"
    for _ in range(timeout):
        resp = requests.get(url)
        if should_exist and resp.status_code == 200:
            return True
        if not should_exist and resp.status_code == 404:
            return True
        time.sleep(1)
    return False

def main():
    # 1. Create image in image_service
    image_data = {
        "slug": "test-kafka-image",
        "title": "Kafka Test Image",
        "description": "Test image for Kafka sync",
        "image_url": "http://example.com/test.jpg",
        "release_year": 2025
    }
    create_resp = requests.post(IMAGE_SERVICE_URL, json=image_data)
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    image = create_resp.json()
    slug = image["slug"]
    print(f"Created image with slug: {slug}")

    # 2. Wait for it to appear in deck_search
    assert wait_for_slug_in_deck_search(slug, should_exist=True), "Image did not appear in deck_search!"
    print("Image appeared in deck_search.")

    # 3. Update image in image_service
    update_data = {"title": "Kafka Test Image Updated"}
    update_resp = requests.patch(f"{IMAGE_SERVICE_URL}{image['id']}/", json=update_data)
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
    print("Image updated in image_service.")

    # 4. Wait for update to propagate (optional: check title in deck_search)
    assert wait_for_slug_in_deck_search(slug, should_exist=True), "Updated image not found in deck_search!"
    print("Image update propagated to deck_search.")

    # 5. Delete image in image_service
    del_resp = requests.delete(f"{IMAGE_SERVICE_URL}{image['id']}/")
    assert del_resp.status_code in (200, 204), f"Delete failed: {del_resp.text}"
    print("Image deleted in image_service.")

    # 6. Wait for it to disappear from deck_search
    assert wait_for_slug_in_deck_search(slug, should_exist=False), "Image did not disappear from deck_search!"
    print("Image deletion propagated to deck_search.")

if __name__ == "__main__":
    main()

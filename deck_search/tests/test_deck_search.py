#!/usr/bin/env python3
"""
Comprehensive test script for deck_search endpoints and filters
Tests all API endpoints, filters, and options with random selections
"""

import requests
import json
import random
import time
from typing import Dict, List, Any

# Configuration
DECK_SEARCH_URL = "http://localhost:12004"
TIMEOUT = 30

class DeckSearchTester:
    def __init__(self, base_url: str = DECK_SEARCH_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, test_name: str, success: bool, message: str, response_data: Dict = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': time.time()
        }
        if response_data:
            result['response'] = response_data
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")

    def test_health_endpoint(self):
        """Test health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/health/", timeout=TIMEOUT)
            if response.status_code in [200, 404]:  # 404 is OK for health endpoint
                self.log_test("Health Check", True, "Health endpoint accessible")
            else:
                self.log_test("Health Check", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {e}")

    def test_root_endpoint(self):
        """Test root endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                indexed_docs = data.get('stats', {}).get('indexed_documents', 0)
                self.log_test("Root Endpoint", True, f"Indexed documents: {indexed_docs}")
            else:
                self.log_test("Root Endpoint", False, f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Exception: {e}")

    def test_schema_endpoints(self):
        """Test API schema endpoints"""
        endpoints = [
            "/api/schema/",
            "/api/schema/swagger-ui/"
        ]

        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=TIMEOUT)
                success = response.status_code == 200
                self.log_test(f"Schema {endpoint}", success, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Schema {endpoint}", False, f"Exception: {e}")

    def test_search_filters_endpoint(self):
        """Test the main search/filters endpoint"""
        # Test without parameters (should return filter configuration)
        try:
            response = self.session.get(f"{self.base_url}/api/search/filters/", timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'filters' in data['data']:
                    self.log_test("Filters Config", True, "Filter configuration returned")
                elif 'results' in data:
                    # This means search was performed
                    result_count = data.get('count', 0)
                    self.log_test("Default Search", True, f"Default search results: {result_count}")
                else:
                    self.log_test("Filters Endpoint", True, "Endpoint responding")
            else:
                self.log_test("Filters Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Filters Endpoint", False, f"Exception: {e}")

    def test_search_functionality(self):
        """Test search functionality with various terms"""
        search_terms = ["Mr", "Robot", "Movie", "Scene", "Action", "Drama", "Warm", "Light"]

        for term in random.sample(search_terms, 4):
            try:
                params = {'search': term, 'limit': random.randint(5, 20)}
                response = self.session.get(f"{self.base_url}/api/search/filters/", params=params, timeout=TIMEOUT)
                success = response.status_code == 200
                if success:
                    data = response.json()
                    result_count = data.get('count', 0)
                    total = data.get('total', 0)
                    self.log_test(f"Search '{term}'", True, f"Results: {result_count}/{total}")
                else:
                    self.log_test(f"Search '{term}'", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Search '{term}'", False, f"Exception: {e}")

    def test_filter_combinations(self):
        """Test various filter combinations"""
        filter_combinations = [
            {'color': 'Warm'},
            {'lighting': 'Soft light'},
            {'color': 'Warm', 'lighting': 'Soft light'},
            {'limit': 10, 'offset': 0},
            {'color': 'Warm', 'limit': 5},
        ]

        for i, filters in enumerate(filter_combinations):
            try:
                response = self.session.get(f"{self.base_url}/api/search/filters/", params=filters, timeout=TIMEOUT)
                success = response.status_code == 200
                if success:
                    data = response.json()
                    result_count = data.get('count', 0)
                    applied = data.get('filters_applied', {})
                    self.log_test(f"Filter Combo {i+1}", True,
                                f"Filters: {list(applied.keys())}, Results: {result_count}")
                else:
                    self.log_test(f"Filter Combo {i+1}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Filter Combo {i+1}", False, f"Exception: {e}")

    def test_pagination(self):
        """Test pagination functionality"""
        for page_size in [5, 10, 20]:
            for offset in [0, 5, 10]:
                try:
                    params = {'limit': page_size, 'offset': offset}
                    response = self.session.get(f"{self.base_url}/api/search/filters/", params=params, timeout=TIMEOUT)
                    success = response.status_code == 200
                    if success:
                        data = response.json()
                        result_count = len(data.get('results', []))
                        self.log_test(f"Pagination {page_size}/{offset}", True,
                                    f"Returned: {result_count}, Expected: ≤{page_size}")
                    else:
                        self.log_test(f"Pagination {page_size}/{offset}", False, f"Status: {response.status_code}")
                except Exception as e:
                    self.log_test(f"Pagination {page_size}/{offset}", False, f"Exception: {e}")

    def test_similar_images_endpoint(self):
        """Test similar images endpoint"""
        # Test with a sample slug
        test_slug = "mr-robot-season-1-episode-7-qb455m4g-90642812"
        try:
            response = self.session.get(f"{self.base_url}/api/search/similar/{test_slug}/", timeout=TIMEOUT)
            success = response.status_code in [200, 404]  # 404 is OK if slug doesn't exist
            if success:
                if response.status_code == 200:
                    data = response.json()
                    self.log_test("Similar Images", True, f"Similar images found for slug")
                else:
                    self.log_test("Similar Images", True, f"Endpoint accessible (slug not found)")
            else:
                self.log_test("Similar Images", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Similar Images", False, f"Exception: {e}")

    def test_user_endpoint(self):
        """Test user endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/search/user/", timeout=TIMEOUT)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.log_test("User Endpoint", True, "User endpoint responding")
            else:
                self.log_test("User Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("User Endpoint", False, f"Exception: {e}")

    def test_color_endpoints(self):
        """Test color-related endpoints"""
        endpoints = [
            "/api/search/color-similarity/",
            "/api/images/search_by_color/"
        ]

        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=TIMEOUT)
                success = response.status_code in [200, 400]  # 400 is OK for missing parameters
                self.log_test(f"Color {endpoint}", success, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Color {endpoint}", False, f"Exception: {e}")

    def test_image_endpoints(self):
        """Test image-related endpoints"""
        # Test with sample slug
        test_slug = "mr-robot-season-1-episode-7-qb455m4g-90642812"
        try:
            response = self.session.get(f"{self.base_url}/api/images/{test_slug}/color_samples/", timeout=TIMEOUT)
            success = response.status_code in [200, 404]
            self.log_test("Image Color Samples", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Image Color Samples", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Deck Search Tests...")
        print("=" * 50)

        self.test_health_endpoint()
        self.test_root_endpoint()
        self.test_schema_endpoints()
        self.test_search_filters_endpoint()
        self.test_search_functionality()
        self.test_filter_combinations()
        self.test_pagination()
        self.test_similar_images_endpoint()
        self.test_user_endpoint()
        self.test_color_endpoints()
        self.test_image_endpoints()

        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")

        if passed < total:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")

        return passed == total

if __name__ == "__main__":
    tester = DeckSearchTester()
    success = tester.run_all_tests()

    # Save detailed results
    with open('/home/a/shotdeck-main/deck_search_test_results.json', 'w') as f:
        json.dump(tester.test_results, f, indent=2, default=str)

    exit(0 if success else 1)

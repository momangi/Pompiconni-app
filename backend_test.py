#!/usr/bin/env python3
"""
Pompiconni Backend API Test Suite
Tests all backend endpoints as specified in the review request
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://bubbleadmin-fixes.preview.emergentagent.com/api"

class PompiconniAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.token = None
        self.test_results = []
        self.created_theme_id = None
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> tuple:
        """Make HTTP request and return (success, response, error)"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, None, f"Unsupported method: {method}"
            
            return True, response, None
        except requests.exceptions.RequestException as e:
            return False, None, str(e)
    
    def test_public_endpoints(self):
        """Test all public endpoints"""
        print("\n=== Testing Public Endpoints ===")
        
        # Test GET /api/themes - should return 6 themes
        success, response, error = self.make_request("GET", "/themes")
        if not success:
            self.log_test("GET /api/themes", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/themes", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                themes = response.json()
                if len(themes) == 6:
                    self.log_test("GET /api/themes", True, f"Returned {len(themes)} themes as expected")
                else:
                    self.log_test("GET /api/themes", False, f"Expected 6 themes, got {len(themes)}", themes)
            except json.JSONDecodeError:
                self.log_test("GET /api/themes", False, "Invalid JSON response", response.text)
        
        # Test GET /api/illustrations - should return 23 illustrations
        success, response, error = self.make_request("GET", "/illustrations")
        if not success:
            self.log_test("GET /api/illustrations", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/illustrations", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                illustrations = response.json()
                if len(illustrations) == 23:
                    self.log_test("GET /api/illustrations", True, f"Returned {len(illustrations)} illustrations as expected")
                else:
                    self.log_test("GET /api/illustrations", False, f"Expected 23 illustrations, got {len(illustrations)}")
            except json.JSONDecodeError:
                self.log_test("GET /api/illustrations", False, "Invalid JSON response", response.text)
        
        # Test GET /api/bundles - should return 4 bundles
        success, response, error = self.make_request("GET", "/bundles")
        if not success:
            self.log_test("GET /api/bundles", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/bundles", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                bundles = response.json()
                if len(bundles) == 4:
                    self.log_test("GET /api/bundles", True, f"Returned {len(bundles)} bundles as expected")
                else:
                    self.log_test("GET /api/bundles", False, f"Expected 4 bundles, got {len(bundles)}")
            except json.JSONDecodeError:
                self.log_test("GET /api/bundles", False, "Invalid JSON response", response.text)
        
        # Test GET /api/reviews - should return 15 reviews
        success, response, error = self.make_request("GET", "/reviews")
        if not success:
            self.log_test("GET /api/reviews", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/reviews", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                reviews = response.json()
                if len(reviews) == 15:
                    self.log_test("GET /api/reviews", True, f"Returned {len(reviews)} reviews as expected")
                else:
                    self.log_test("GET /api/reviews", False, f"Expected 15 reviews, got {len(reviews)}")
            except json.JSONDecodeError:
                self.log_test("GET /api/reviews", False, "Invalid JSON response", response.text)
        
        # Test GET /api/brand-kit - should return brand kit data
        success, response, error = self.make_request("GET", "/brand-kit")
        if not success:
            self.log_test("GET /api/brand-kit", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/brand-kit", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                brand_kit = response.json()
                required_keys = ["character", "colors", "typography", "styleGuidelines"]
                missing_keys = [key for key in required_keys if key not in brand_kit]
                if not missing_keys:
                    self.log_test("GET /api/brand-kit", True, "Brand kit data returned with all required fields")
                else:
                    self.log_test("GET /api/brand-kit", False, f"Missing required fields: {missing_keys}", brand_kit)
            except json.JSONDecodeError:
                self.log_test("GET /api/brand-kit", False, "Invalid JSON response", response.text)
    
    def test_admin_authentication(self):
        """Test admin login"""
        print("\n=== Testing Admin Authentication ===")
        
        login_data = {
            "email": "admin@pompiconni.it",
            "password": "admin123"
        }
        
        success, response, error = self.make_request("POST", "/admin/login", login_data)
        if not success:
            self.log_test("POST /api/admin/login", False, f"Request failed: {error}")
            return False
        elif response.status_code != 200:
            self.log_test("POST /api/admin/login", False, f"HTTP {response.status_code}: {response.text}")
            return False
        else:
            try:
                login_response = response.json()
                if "token" in login_response and "email" in login_response:
                    self.token = login_response["token"]
                    self.log_test("POST /api/admin/login", True, f"Login successful, token received")
                    return True
                else:
                    self.log_test("POST /api/admin/login", False, "Missing token or email in response", login_response)
                    return False
            except json.JSONDecodeError:
                self.log_test("POST /api/admin/login", False, "Invalid JSON response", response.text)
                return False
    
    def test_admin_dashboard(self):
        """Test admin dashboard with token"""
        print("\n=== Testing Admin Dashboard ===")
        
        if not self.token:
            self.log_test("GET /api/admin/dashboard", False, "No token available - login failed")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        success, response, error = self.make_request("GET", "/admin/dashboard", headers=headers)
        
        if not success:
            self.log_test("GET /api/admin/dashboard", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/admin/dashboard", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                dashboard = response.json()
                required_fields = ["totalIllustrations", "totalThemes", "totalDownloads", "freeCount", "popularIllustrations"]
                missing_fields = [field for field in required_fields if field not in dashboard]
                if not missing_fields:
                    self.log_test("GET /api/admin/dashboard", True, "Dashboard data returned with all required fields")
                else:
                    self.log_test("GET /api/admin/dashboard", False, f"Missing required fields: {missing_fields}", dashboard)
            except json.JSONDecodeError:
                self.log_test("GET /api/admin/dashboard", False, "Invalid JSON response", response.text)
    
    def test_crud_operations(self):
        """Test CRUD operations with authentication"""
        print("\n=== Testing CRUD Operations ===")
        
        if not self.token:
            self.log_test("CRUD Operations", False, "No token available - login failed")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a new theme
        theme_data = {
            "name": "Test Theme",
            "description": "A test theme for API testing",
            "icon": "TestIcon",
            "color": "#FF0000"
        }
        
        success, response, error = self.make_request("POST", "/admin/themes", theme_data, headers)
        if not success:
            self.log_test("POST /api/admin/themes (Create)", False, f"Request failed: {error}")
            return
        elif response.status_code != 200:
            self.log_test("POST /api/admin/themes (Create)", False, f"HTTP {response.status_code}: {response.text}")
            return
        else:
            try:
                created_theme = response.json()
                if "id" in created_theme and created_theme["name"] == theme_data["name"]:
                    self.created_theme_id = created_theme["id"]
                    self.log_test("POST /api/admin/themes (Create)", True, f"Theme created successfully with ID: {self.created_theme_id}")
                else:
                    self.log_test("POST /api/admin/themes (Create)", False, "Invalid theme creation response", created_theme)
                    return
            except json.JSONDecodeError:
                self.log_test("POST /api/admin/themes (Create)", False, "Invalid JSON response", response.text)
                return
        
        # Update the theme
        updated_theme_data = {
            "name": "Updated Test Theme",
            "description": "An updated test theme for API testing",
            "icon": "UpdatedIcon",
            "color": "#00FF00"
        }
        
        success, response, error = self.make_request("PUT", f"/admin/themes/{self.created_theme_id}", updated_theme_data, headers)
        if not success:
            self.log_test("PUT /api/admin/themes (Update)", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("PUT /api/admin/themes (Update)", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                update_response = response.json()
                if update_response.get("success"):
                    self.log_test("PUT /api/admin/themes (Update)", True, "Theme updated successfully")
                else:
                    self.log_test("PUT /api/admin/themes (Update)", False, "Update response indicates failure", update_response)
            except json.JSONDecodeError:
                self.log_test("PUT /api/admin/themes (Update)", False, "Invalid JSON response", response.text)
        
        # Delete the theme
        success, response, error = self.make_request("DELETE", f"/admin/themes/{self.created_theme_id}", headers=headers)
        if not success:
            self.log_test("DELETE /api/admin/themes (Delete)", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("DELETE /api/admin/themes (Delete)", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                delete_response = response.json()
                if delete_response.get("success"):
                    self.log_test("DELETE /api/admin/themes (Delete)", True, "Theme deleted successfully")
                else:
                    self.log_test("DELETE /api/admin/themes (Delete)", False, "Delete response indicates failure", delete_response)
            except json.JSONDecodeError:
                self.log_test("DELETE /api/admin/themes (Delete)", False, "Invalid JSON response", response.text)
    
    def test_filters(self):
        """Test illustration filters"""
        print("\n=== Testing Filters ===")
        
        # Test isFree=true filter
        success, response, error = self.make_request("GET", "/illustrations?isFree=true")
        if not success:
            self.log_test("GET /api/illustrations?isFree=true", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/illustrations?isFree=true", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                free_illustrations = response.json()
                all_free = all(illust.get("isFree", False) for illust in free_illustrations)
                if all_free and len(free_illustrations) > 0:
                    self.log_test("GET /api/illustrations?isFree=true", True, f"Returned {len(free_illustrations)} free illustrations")
                elif len(free_illustrations) == 0:
                    self.log_test("GET /api/illustrations?isFree=true", False, "No free illustrations returned")
                else:
                    self.log_test("GET /api/illustrations?isFree=true", False, "Some returned illustrations are not free")
            except json.JSONDecodeError:
                self.log_test("GET /api/illustrations?isFree=true", False, "Invalid JSON response", response.text)
        
        # Test themeId=mestieri filter
        success, response, error = self.make_request("GET", "/illustrations?themeId=mestieri")
        if not success:
            self.log_test("GET /api/illustrations?themeId=mestieri", False, f"Request failed: {error}")
        elif response.status_code != 200:
            self.log_test("GET /api/illustrations?themeId=mestieri", False, f"HTTP {response.status_code}: {response.text}")
        else:
            try:
                mestieri_illustrations = response.json()
                all_mestieri = all(illust.get("themeId") == "mestieri" for illust in mestieri_illustrations)
                if all_mestieri and len(mestieri_illustrations) > 0:
                    self.log_test("GET /api/illustrations?themeId=mestieri", True, f"Returned {len(mestieri_illustrations)} mestieri illustrations")
                elif len(mestieri_illustrations) == 0:
                    self.log_test("GET /api/illustrations?themeId=mestieri", False, "No mestieri illustrations returned")
                else:
                    self.log_test("GET /api/illustrations?themeId=mestieri", False, "Some returned illustrations are not from mestieri theme")
            except json.JSONDecodeError:
                self.log_test("GET /api/illustrations?themeId=mestieri", False, "Invalid JSON response", response.text)
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"🚀 Starting Pompiconni Backend API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in order
        self.test_public_endpoints()
        login_success = self.test_admin_authentication()
        if login_success:
            self.test_admin_dashboard()
            self.test_crud_operations()
        self.test_filters()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = PompiconniAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
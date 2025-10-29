#!/usr/bin/env python3
"""
Test script for QP-IAC CDN Headers Project endpoints
"""

import requests
import json
import sys
import time
from typing import Optional

class CDNHeadersTestSuite:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.jwt_token: Optional[str] = None
        
    def test_health_check(self):
        """Test health check endpoint"""
        print("🏥 Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_login(self, username: str = "admin", password: str = "password123"):
        """Test login and JWT token generation"""
        print("🔐 Testing login...")
        try:
            payload = {"username": username, "password": password}
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data["access_token"]
                print(f"✅ Login successful, token expires in {data['expires_in']} seconds")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_user_info(self):
        """Test authenticated user info endpoint"""
        print("👤 Testing user info...")
        if not self.jwt_token:
            print("❌ No JWT token available, skipping user info test")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ User info retrieved: {data['username']} (authenticated: {data['authenticated']})")
                if data.get('cdn_validated'):
                    print("🌐 Request validated by CDN")
                return True
            else:
                print(f"❌ User info failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ User info error: {e}")
            return False
    
    def test_protected_endpoint(self):
        """Test protected API endpoint"""
        print("🔒 Testing protected endpoint...")
        if not self.jwt_token:
            print("❌ No JWT token available, skipping protected endpoint test")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = self.session.get(f"{self.base_url}/api/protected", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Protected endpoint access granted for user: {data['user']}")
                print(f"   Request source: {data['request_source']}")
                return True
            else:
                print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Protected endpoint error: {e}")
            return False
    
    def test_headers_debug(self):
        """Test headers debug endpoint"""
        print("🔍 Testing headers debug...")
        try:
            response = self.session.get(f"{self.base_url}/debug/headers")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Headers debug successful")
                print(f"   CDN validated: {data['cdn_validated']}")
                print(f"   Edge processed: {data['edge_processed']}")
                if data.get('request_id'):
                    print(f"   Request ID: {data['request_id']}")
                return True
            else:
                print(f"❌ Headers debug failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Headers debug error: {e}")
            return False
    
    def test_api_status(self):
        """Test API status endpoint"""
        print("📊 Testing API status...")
        try:
            response = self.session.get(f"{self.base_url}/api/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API status: {data['api_status']}")
                print(f"   Version: {data['version']}")
                print(f"   Environment: {data['environment']}")
                features = data.get('features', {})
                print(f"   Features: JWT({features.get('jwt_validation')}), CDN({features.get('cdn_integration')})")
                return True
            else:
                print(f"❌ API status failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ API status error: {e}")
            return False
    
    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        print("🚫 Testing unauthorized access...")
        try:
            # Test without token
            response = self.session.get(f"{self.base_url}/auth/me")
            if response.status_code == 401:
                print("✅ Unauthorized access properly blocked (no token)")
            else:
                print(f"❌ Unauthorized access not blocked: {response.status_code}")
                return False
            
            # Test with invalid token
            headers = {"Authorization": "Bearer invalid-token"}
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 401:
                print("✅ Unauthorized access properly blocked (invalid token)")
                return True
            else:
                print(f"❌ Invalid token not blocked: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Unauthorized access test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all test cases"""
        print("🧪 Starting QP-IAC CDN Headers Project Test Suite")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("API Status", self.test_api_status),
            ("Headers Debug", self.test_headers_debug),
            ("Login", self.test_login),
            ("User Info", self.test_user_info),
            ("Protected Endpoint", self.test_protected_endpoint),
            ("Unauthorized Access", self.test_unauthorized_access),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            if test_func():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 60)
        print(f"🏁 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your CDN Headers Project is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the logs above.")
            return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_endpoints.py <base_url>")
        print("Example: python test_endpoints.py https://d1234567890.cloudfront.net")
        sys.exit(1)
    
    base_url = sys.argv[1]
    test_suite = CDNHeadersTestSuite(base_url)
    
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
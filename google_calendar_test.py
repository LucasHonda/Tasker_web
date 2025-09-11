#!/usr/bin/env python3
"""
Google Calendar Integration Testing
Tests the new real Google Calendar integration features including:
- Calendar Authorization Status
- Google OAuth Flow
- Real Calendar Events with different auth states
- Token Management and Refresh
- Authentication Security
- Error Handling
"""

import asyncio
import httpx
import json
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Configuration
BACKEND_URL = "https://schedule-buddy-62.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

class GoogleCalendarTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        self.session_token = None
        self.user_id = None
        self.test_results = []
        
    async def log_result(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    async def setup_mock_user(self):
        """Create a mock user session for testing protected endpoints"""
        try:
            # Create mock user data
            user_data = {
                "id": str(uuid.uuid4()),
                "email": "calendar.test@example.com",
                "name": "Calendar Test User",
                "picture": "https://example.com/avatar.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            await self.db.users.insert_one(user_data)
            
            self.session_token = user_data["session_token"]
            self.user_id = user_data["id"]
            
            await self.log_result("Setup Mock User", True, "Mock user created successfully")
            return True
            
        except Exception as e:
            await self.log_result("Setup Mock User", False, f"Failed to create mock user: {str(e)}")
            return False
    
    async def setup_mock_user_with_google_tokens(self):
        """Create a mock user with Google OAuth tokens for testing authorized scenarios"""
        try:
            # Create mock user data with Google tokens
            user_data = {
                "id": str(uuid.uuid4()),
                "email": "authorized.calendar.test@example.com",
                "name": "Authorized Calendar Test User",
                "picture": "https://example.com/avatar.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                # Mock Google OAuth tokens
                "google_access_token": "mock_access_token_12345",
                "google_refresh_token": "mock_refresh_token_67890",
                "google_token_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }
            
            # Insert into database
            await self.db.users.insert_one(user_data)
            
            self.authorized_session_token = user_data["session_token"]
            self.authorized_user_id = user_data["id"]
            
            await self.log_result("Setup Authorized Mock User", True, "Mock user with Google tokens created successfully")
            return True
            
        except Exception as e:
            await self.log_result("Setup Authorized Mock User", False, f"Failed to create authorized mock user: {str(e)}")
            return False
    
    async def setup_mock_user_with_expired_tokens(self):
        """Create a mock user with expired Google OAuth tokens for testing token refresh scenarios"""
        try:
            # Create mock user data with expired Google tokens
            user_data = {
                "id": str(uuid.uuid4()),
                "email": "expired.calendar.test@example.com",
                "name": "Expired Calendar Test User",
                "picture": "https://example.com/avatar.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                # Mock expired Google OAuth tokens
                "google_access_token": "expired_access_token_12345",
                "google_refresh_token": "mock_refresh_token_67890",
                "google_token_expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()  # Expired
            }
            
            # Insert into database
            await self.db.users.insert_one(user_data)
            
            self.expired_session_token = user_data["session_token"]
            self.expired_user_id = user_data["id"]
            
            await self.log_result("Setup Expired Token Mock User", True, "Mock user with expired Google tokens created successfully")
            return True
            
        except Exception as e:
            await self.log_result("Setup Expired Token Mock User", False, f"Failed to create expired token mock user: {str(e)}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            # Remove all test users
            user_ids = [self.user_id, getattr(self, 'authorized_user_id', None), getattr(self, 'expired_user_id', None)]
            for user_id in user_ids:
                if user_id:
                    await self.db.users.delete_one({"id": user_id})
            
            await self.log_result("Cleanup Test Data", True, "Test data cleaned up successfully")
            
        except Exception as e:
            await self.log_result("Cleanup Test Data", False, f"Failed to cleanup: {str(e)}")
    
    async def test_calendar_auth_status_unauthorized(self):
        """Test GET /api/calendar/auth-status for unauthorized user"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "authorized" in data and data["authorized"] == False and "auth_url" in data:
                    await self.log_result("Calendar Auth Status - Unauthorized", True, "Correctly returned unauthorized status", data)
                else:
                    await self.log_result("Calendar Auth Status - Unauthorized", False, "Invalid response format", data)
            else:
                await self.log_result("Calendar Auth Status - Unauthorized", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Auth Status - Unauthorized", False, f"Request failed: {str(e)}")
    
    async def test_calendar_auth_status_authorized(self):
        """Test GET /api/calendar/auth-status for authorized user"""
        try:
            headers = {"Authorization": f"Bearer {self.authorized_session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "authorized" in data and data["authorized"] == True:
                    await self.log_result("Calendar Auth Status - Authorized", True, "Correctly returned authorized status", data)
                else:
                    await self.log_result("Calendar Auth Status - Authorized", False, "Invalid response format", data)
            else:
                await self.log_result("Calendar Auth Status - Authorized", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Auth Status - Authorized", False, f"Request failed: {str(e)}")
    
    async def test_calendar_auth_status_expired_tokens(self):
        """Test GET /api/calendar/auth-status for user with expired tokens"""
        try:
            headers = {"Authorization": f"Bearer {self.expired_session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "authorized" in data and data["authorized"] == False and "message" in data:
                    await self.log_result("Calendar Auth Status - Expired Tokens", True, "Correctly handled expired tokens", data)
                else:
                    await self.log_result("Calendar Auth Status - Expired Tokens", False, "Invalid response format", data)
            else:
                await self.log_result("Calendar Auth Status - Expired Tokens", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Auth Status - Expired Tokens", False, f"Request failed: {str(e)}")
    
    async def test_calendar_auth_status_without_auth(self):
        """Test GET /api/calendar/auth-status without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status")
            
            if response.status_code == 401:
                await self.log_result("Calendar Auth Status - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Calendar Auth Status - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Auth Status - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_google_oauth_initiate(self):
        """Test GET /api/auth/google/calendar to initiate OAuth flow"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/auth/google/calendar", headers=headers, follow_redirects=False)
            
            # Should redirect to Google OAuth
            if response.status_code in [302, 307, 308]:
                location = response.headers.get("location", "")
                if "accounts.google.com" in location and "oauth2" in location:
                    await self.log_result("Google OAuth Initiate", True, "Successfully initiated Google OAuth flow", {"redirect_url": location})
                else:
                    await self.log_result("Google OAuth Initiate", False, "Invalid redirect URL", {"location": location})
            else:
                await self.log_result("Google OAuth Initiate", False, f"Expected redirect, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Google OAuth Initiate", False, f"Request failed: {str(e)}")
    
    async def test_google_oauth_initiate_without_auth(self):
        """Test GET /api/auth/google/calendar without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/auth/google/calendar", follow_redirects=False)
            
            if response.status_code == 401:
                await self.log_result("Google OAuth Initiate - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Google OAuth Initiate - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Google OAuth Initiate - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_unauthorized(self):
        """Test GET /api/calendar/events for unauthorized user"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/events", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Should return authorization required event
                    first_event = data[0]
                    if first_event.get("id") == "auth-required" and "Authorization Required" in first_event.get("title", ""):
                        await self.log_result("Calendar Events - Unauthorized", True, "Correctly returned authorization required event", {"event_count": len(data)})
                    else:
                        await self.log_result("Calendar Events - Unauthorized", False, "Expected authorization required event", first_event)
                else:
                    await self.log_result("Calendar Events - Unauthorized", False, "Expected non-empty list", data)
            else:
                await self.log_result("Calendar Events - Unauthorized", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events - Unauthorized", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_authorized(self):
        """Test GET /api/calendar/events for authorized user (will fallback to mock data)"""
        try:
            headers = {"Authorization": f"Bearer {self.authorized_session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/events", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Should return mock events since we don't have real Google Calendar API access
                    first_event = data[0]
                    required_fields = ["id", "title", "start_time", "end_time", "calendar_id"]
                    if all(field in first_event for field in required_fields):
                        await self.log_result("Calendar Events - Authorized", True, f"Retrieved {len(data)} calendar events", {"event_count": len(data)})
                    else:
                        await self.log_result("Calendar Events - Authorized", False, "Events missing required fields", first_event)
                else:
                    await self.log_result("Calendar Events - Authorized", False, "Expected non-empty list", data)
            else:
                await self.log_result("Calendar Events - Authorized", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events - Authorized", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_with_date_range(self):
        """Test GET /api/calendar/events with date range parameters"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            start_date = datetime.now(timezone.utc).isoformat()
            end_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            
            response = await self.client.get(
                f"{BACKEND_URL}/calendar/events?start_date={start_date}&end_date={end_date}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    await self.log_result("Calendar Events - Date Range", True, f"Retrieved {len(data)} events with date range", {"event_count": len(data)})
                else:
                    await self.log_result("Calendar Events - Date Range", False, "Expected list response", data)
            else:
                await self.log_result("Calendar Events - Date Range", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events - Date Range", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_without_auth(self):
        """Test GET /api/calendar/events without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/calendar/events")
            
            if response.status_code == 401:
                await self.log_result("Calendar Events - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Calendar Events - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_calendar_test_google_access(self):
        """Test GET /api/calendar/test-google-access endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and "message" in data:
                    await self.log_result("Calendar Test Google Access", True, "Test endpoint working correctly", data)
                else:
                    await self.log_result("Calendar Test Google Access", False, "Invalid response format", data)
            else:
                await self.log_result("Calendar Test Google Access", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Test Google Access", False, f"Request failed: {str(e)}")
    
    async def test_calendar_test_google_access_without_auth(self):
        """Test GET /api/calendar/test-google-access without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access")
            
            if response.status_code == 401:
                await self.log_result("Calendar Test Google Access - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Calendar Test Google Access - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Test Google Access - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_invalid_session_token(self):
        """Test calendar endpoints with invalid session token"""
        try:
            headers = {"Authorization": "Bearer invalid_token_12345"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status", headers=headers)
            
            if response.status_code == 401:
                await self.log_result("Invalid Session Token", True, "Correctly rejected invalid session token")
            else:
                await self.log_result("Invalid Session Token", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Invalid Session Token", False, f"Request failed: {str(e)}")
    
    async def test_expired_session_token(self):
        """Test calendar endpoints with expired session token"""
        try:
            # Create user with expired session
            expired_user_data = {
                "id": str(uuid.uuid4()),
                "email": "expired.session@example.com",
                "name": "Expired Session User",
                "picture": "https://example.com/avatar.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),  # Expired
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.users.insert_one(expired_user_data)
            
            headers = {"Authorization": f"Bearer {expired_user_data['session_token']}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/auth-status", headers=headers)
            
            if response.status_code == 401:
                await self.log_result("Expired Session Token", True, "Correctly rejected expired session token")
            else:
                await self.log_result("Expired Session Token", False, f"Expected 401, got {response.status_code}", response.text)
            
            # Cleanup
            await self.db.users.delete_one({"id": expired_user_data["id"]})
                
        except Exception as e:
            await self.log_result("Expired Session Token", False, f"Request failed: {str(e)}")
    
    async def run_all_tests(self):
        """Run all Google Calendar integration tests"""
        print("🚀 Starting Google Calendar Integration Testing...")
        print("=" * 70)
        
        # Setup test users
        setup_success = await self.setup_mock_user()
        if not setup_success:
            print("❌ Failed to setup mock user. Aborting tests.")
            return
        
        authorized_setup_success = await self.setup_mock_user_with_google_tokens()
        if not authorized_setup_success:
            print("❌ Failed to setup authorized mock user. Aborting tests.")
            return
        
        expired_setup_success = await self.setup_mock_user_with_expired_tokens()
        if not expired_setup_success:
            print("❌ Failed to setup expired token mock user. Aborting tests.")
            return
        
        # Run Calendar Authorization Status Tests
        print("\n📋 Testing Calendar Authorization Status...")
        await self.test_calendar_auth_status_unauthorized()
        await self.test_calendar_auth_status_authorized()
        await self.test_calendar_auth_status_expired_tokens()
        await self.test_calendar_auth_status_without_auth()
        
        # Run Google OAuth Flow Tests
        print("\n🔐 Testing Google OAuth Flow...")
        await self.test_google_oauth_initiate()
        await self.test_google_oauth_initiate_without_auth()
        
        # Run Calendar Events Tests
        print("\n📅 Testing Calendar Events...")
        await self.test_calendar_events_unauthorized()
        await self.test_calendar_events_authorized()
        await self.test_calendar_events_with_date_range()
        await self.test_calendar_events_without_auth()
        
        # Run Test Google Access Tests
        print("\n🧪 Testing Google Access Test Endpoint...")
        await self.test_calendar_test_google_access()
        await self.test_calendar_test_google_access_without_auth()
        
        # Run Security Tests
        print("\n🔒 Testing Authentication Security...")
        await self.test_invalid_session_token()
        await self.test_expired_session_token()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 GOOGLE CALENDAR INTEGRATION TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n" + "=" * 70)
        
        # Close connections
        await self.client.aclose()
        self.mongo_client.close()
        
        return passed, failed

async def main():
    """Main test runner"""
    tester = GoogleCalendarTester()
    passed, failed = await tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
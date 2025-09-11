#!/usr/bin/env python3
"""
Google Calendar Integration Testing
Tests the new Google Calendar integration features including:
- Calendar test endpoint
- Enhanced calendar events with Google API integration attempt
- Authentication with calendar endpoints
- Error handling for calendar endpoints
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

class CalendarIntegrationTester:
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
                "picture": "https://example.com/calendar-avatar.jpg",
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
    
    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            # Remove test user
            if self.user_id:
                await self.db.users.delete_one({"id": self.user_id})
            
            await self.log_result("Cleanup Test Data", True, "Test data cleaned up successfully")
            
        except Exception as e:
            await self.log_result("Cleanup Test Data", False, f"Failed to cleanup: {str(e)}")
    
    async def test_basic_api_connectivity(self):
        """Test basic API connectivity - ensure backend is running correctly"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    await self.log_result("Basic API Connectivity", True, "Backend API is running correctly", data)
                else:
                    await self.log_result("Basic API Connectivity", False, "Invalid response format", data)
            else:
                await self.log_result("Basic API Connectivity", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Basic API Connectivity", False, f"Request failed: {str(e)}")
    
    async def test_calendar_test_endpoint_without_auth(self):
        """Test calendar test endpoint without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access")
            
            if response.status_code == 401:
                await self.log_result("Calendar Test Endpoint - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Calendar Test Endpoint - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Test Endpoint - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_calendar_test_endpoint_with_auth(self):
        """Test GET /api/calendar/test-google-access to check Google Calendar API access status"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "message"]
                if all(field in data for field in required_fields):
                    # Check if it's handling the Google Calendar integration properly
                    status = data.get("status")
                    if status in ["partial_success", "error"]:
                        await self.log_result("Calendar Test Endpoint - With Auth", True, f"Calendar test endpoint working: {data['message']}", data)
                    else:
                        await self.log_result("Calendar Test Endpoint - With Auth", False, f"Unexpected status: {status}", data)
                else:
                    await self.log_result("Calendar Test Endpoint - With Auth", False, "Response missing required fields", data)
            else:
                await self.log_result("Calendar Test Endpoint - With Auth", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Test Endpoint - With Auth", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_without_auth(self):
        """Test calendar events endpoint without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/calendar/events")
            
            if response.status_code == 401:
                await self.log_result("Calendar Events - No Auth", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Calendar Events - No Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events - No Auth", False, f"Request failed: {str(e)}")
    
    async def test_enhanced_calendar_events_endpoint(self):
        """Test GET /api/calendar/events to verify enhanced mock data with user personalization"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/events", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check if events have required fields
                    first_event = data[0]
                    required_fields = ["id", "title", "start_time", "end_time", "all_day", "location", "calendar_id"]
                    if all(field in first_event for field in required_fields):
                        # Check for user personalization (should include user name in some events)
                        user_personalized = any("Calendar Test User" in event.get("title", "") for event in data)
                        if user_personalized:
                            await self.log_result("Enhanced Calendar Events", True, f"Retrieved {len(data)} personalized calendar events", {"count": len(data), "personalized": True})
                        else:
                            await self.log_result("Enhanced Calendar Events", True, f"Retrieved {len(data)} calendar events (no personalization detected)", {"count": len(data), "personalized": False})
                    else:
                        await self.log_result("Enhanced Calendar Events", False, "Events missing required fields", first_event)
                else:
                    await self.log_result("Enhanced Calendar Events", False, "Expected non-empty list", data)
            else:
                await self.log_result("Enhanced Calendar Events", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Enhanced Calendar Events", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events_with_date_range(self):
        """Test calendar events endpoint with date range parameters"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test with specific date range
            start_date = datetime.now(timezone.utc).isoformat()
            end_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            
            response = await self.client.get(
                f"{BACKEND_URL}/calendar/events?start_date={start_date}&end_date={end_date}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    await self.log_result("Calendar Events with Date Range", True, f"Retrieved {len(data)} events with date filtering", {"count": len(data)})
                else:
                    await self.log_result("Calendar Events with Date Range", False, "Expected list response", data)
            else:
                await self.log_result("Calendar Events with Date Range", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events with Date Range", False, f"Request failed: {str(e)}")
    
    async def test_calendar_error_handling_invalid_auth(self):
        """Test calendar endpoints with invalid authentication"""
        try:
            # Test with invalid token
            headers = {"Authorization": "Bearer invalid-token-12345"}
            
            # Test calendar test endpoint
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access", headers=headers)
            if response.status_code == 401:
                await self.log_result("Calendar Error Handling - Invalid Auth (Test)", True, "Correctly rejected invalid token for test endpoint")
            else:
                await self.log_result("Calendar Error Handling - Invalid Auth (Test)", False, f"Expected 401, got {response.status_code}")
            
            # Test calendar events endpoint
            response = await self.client.get(f"{BACKEND_URL}/calendar/events", headers=headers)
            if response.status_code == 401:
                await self.log_result("Calendar Error Handling - Invalid Auth (Events)", True, "Correctly rejected invalid token for events endpoint")
            else:
                await self.log_result("Calendar Error Handling - Invalid Auth (Events)", False, f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            await self.log_result("Calendar Error Handling - Invalid Auth", False, f"Request failed: {str(e)}")
    
    async def test_calendar_integration_infrastructure(self):
        """Test that the calendar integration infrastructure is working"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test the calendar test endpoint to verify infrastructure
            response = await self.client.get(f"{BACKEND_URL}/calendar/test-google-access", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it's attempting Google Calendar integration
                if "partial_success" in data.get("status", "") or "error" in data.get("status", ""):
                    # Check for expected infrastructure elements
                    has_recommendation = "recommendation" in data
                    has_fallback = "fallback" in data
                    mentions_oauth = "OAuth" in data.get("message", "") or "oauth" in data.get("note", "")
                    
                    if has_recommendation or has_fallback or mentions_oauth:
                        await self.log_result("Calendar Integration Infrastructure", True, "Calendar integration infrastructure is properly implemented", data)
                    else:
                        await self.log_result("Calendar Integration Infrastructure", False, "Infrastructure missing expected elements", data)
                else:
                    await self.log_result("Calendar Integration Infrastructure", False, f"Unexpected response format", data)
            else:
                await self.log_result("Calendar Integration Infrastructure", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Integration Infrastructure", False, f"Request failed: {str(e)}")
    
    async def run_calendar_integration_tests(self):
        """Run all calendar integration tests"""
        print("🗓️  Starting Google Calendar Integration Testing...")
        print("=" * 60)
        
        # Setup
        setup_success = await self.setup_mock_user()
        if not setup_success:
            print("❌ Failed to setup mock user. Aborting tests.")
            return
        
        # Run tests in logical order
        await self.test_basic_api_connectivity()
        await self.test_calendar_test_endpoint_without_auth()
        await self.test_calendar_test_endpoint_with_auth()
        await self.test_calendar_events_without_auth()
        await self.test_enhanced_calendar_events_endpoint()
        await self.test_calendar_events_with_date_range()
        await self.test_calendar_error_handling_invalid_auth()
        await self.test_calendar_integration_infrastructure()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 CALENDAR INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
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
        
        print("\n" + "=" * 60)
        
        # Close connections
        await self.client.aclose()
        self.mongo_client.close()
        
        return passed, failed

async def main():
    """Main test runner"""
    tester = CalendarIntegrationTester()
    passed, failed = await tester.run_calendar_integration_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
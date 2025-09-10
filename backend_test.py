#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Calendar & Task Management System
Tests all API endpoints including authentication, task management, calendar, and dashboard
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

class BackendTester:
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
                "email": "test.user@example.com",
                "name": "Test User",
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
    
    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            # Remove test user
            if self.user_id:
                await self.db.users.delete_one({"id": self.user_id})
            
            # Remove test tasks
            if self.user_id:
                await self.db.tasks.delete_many({"user_id": self.user_id})
            
            await self.log_result("Cleanup Test Data", True, "Test data cleaned up successfully")
            
        except Exception as e:
            await self.log_result("Cleanup Test Data", False, f"Failed to cleanup: {str(e)}")
    
    async def test_basic_health_check(self):
        """Test basic API health check endpoint"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    await self.log_result("Basic Health Check", True, "API health check successful", data)
                else:
                    await self.log_result("Basic Health Check", False, "Invalid response format", data)
            else:
                await self.log_result("Basic Health Check", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Basic Health Check", False, f"Request failed: {str(e)}")
    
    async def test_auth_me_without_token(self):
        """Test /auth/me endpoint without authentication (should fail)"""
        try:
            response = await self.client.get(f"{BACKEND_URL}/auth/me")
            
            if response.status_code == 401:
                await self.log_result("Auth Me Without Token", True, "Correctly rejected unauthenticated request")
            else:
                await self.log_result("Auth Me Without Token", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Auth Me Without Token", False, f"Request failed: {str(e)}")
    
    async def test_auth_me_with_token(self):
        """Test /auth/me endpoint with valid authentication"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "user_id" in data and "email" in data:
                    await self.log_result("Auth Me With Token", True, "Successfully retrieved user info", data)
                else:
                    await self.log_result("Auth Me With Token", False, "Invalid response format", data)
            else:
                await self.log_result("Auth Me With Token", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Auth Me With Token", False, f"Request failed: {str(e)}")
    
    async def test_create_task(self):
        """Test creating a new task"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            task_data = {
                "title": "Test Task for Backend Testing",
                "description": "This is a comprehensive test task with all features",
                "category": "Testing",
                "priority": "High",
                "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                "reminder": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
            }
            
            response = await self.client.post(
                f"{BACKEND_URL}/tasks",
                headers=headers,
                json=task_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["title"] == task_data["title"]:
                    self.test_task_id = data["id"]  # Store for later tests
                    await self.log_result("Create Task", True, "Task created successfully", data)
                else:
                    await self.log_result("Create Task", False, "Invalid response format", data)
            else:
                await self.log_result("Create Task", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Create Task", False, f"Request failed: {str(e)}")
    
    async def test_get_tasks(self):
        """Test retrieving tasks"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/tasks", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    await self.log_result("Get Tasks", True, f"Retrieved {len(data)} tasks", {"count": len(data)})
                else:
                    await self.log_result("Get Tasks", False, "Expected list response", data)
            else:
                await self.log_result("Get Tasks", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Get Tasks", False, f"Request failed: {str(e)}")
    
    async def test_get_tasks_with_filters(self):
        """Test retrieving tasks with category and completion filters"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test category filter
            response = await self.client.get(
                f"{BACKEND_URL}/tasks?category=Testing",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.log_result("Get Tasks with Category Filter", True, f"Retrieved {len(data)} tasks with category filter")
            else:
                await self.log_result("Get Tasks with Category Filter", False, f"HTTP {response.status_code}", response.text)
            
            # Test completion filter
            response = await self.client.get(
                f"{BACKEND_URL}/tasks?completed=false",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.log_result("Get Tasks with Completion Filter", True, f"Retrieved {len(data)} incomplete tasks")
            else:
                await self.log_result("Get Tasks with Completion Filter", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Get Tasks with Filters", False, f"Request failed: {str(e)}")
    
    async def test_update_task(self):
        """Test updating a task"""
        try:
            if not hasattr(self, 'test_task_id'):
                await self.log_result("Update Task", False, "No test task ID available")
                return
            
            headers = {"Authorization": f"Bearer {self.session_token}"}
            update_data = {
                "title": "Updated Test Task",
                "completed": True,
                "priority": "Medium"
            }
            
            response = await self.client.put(
                f"{BACKEND_URL}/tasks/{self.test_task_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["title"] == update_data["title"] and data["completed"] == True:
                    await self.log_result("Update Task", True, "Task updated successfully", data)
                else:
                    await self.log_result("Update Task", False, "Task not updated correctly", data)
            else:
                await self.log_result("Update Task", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Update Task", False, f"Request failed: {str(e)}")
    
    async def test_get_task_categories(self):
        """Test retrieving unique task categories"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/tasks/categories", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    await self.log_result("Get Task Categories", True, f"Retrieved {len(data)} categories", data)
                else:
                    await self.log_result("Get Task Categories", False, "Expected list response", data)
            else:
                await self.log_result("Get Task Categories", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Get Task Categories", False, f"Request failed: {str(e)}")
    
    async def test_calendar_events(self):
        """Test retrieving calendar events"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/calendar/events", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check if events have required fields
                    first_event = data[0]
                    required_fields = ["id", "title", "start_time", "end_time"]
                    if all(field in first_event for field in required_fields):
                        await self.log_result("Calendar Events", True, f"Retrieved {len(data)} calendar events", {"count": len(data)})
                    else:
                        await self.log_result("Calendar Events", False, "Events missing required fields", first_event)
                else:
                    await self.log_result("Calendar Events", False, "Expected non-empty list", data)
            else:
                await self.log_result("Calendar Events", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Calendar Events", False, f"Request failed: {str(e)}")
    
    async def test_dashboard_summary(self):
        """Test dashboard summary endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/dashboard/summary", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["task_stats", "today_tasks_count", "upcoming_tasks_count"]
                if all(field in data for field in required_fields):
                    # Check task_stats structure
                    task_stats = data["task_stats"]
                    if all(key in task_stats for key in ["total", "completed", "pending"]):
                        await self.log_result("Dashboard Summary", True, "Dashboard summary retrieved successfully", data)
                    else:
                        await self.log_result("Dashboard Summary", False, "task_stats missing required fields", data)
                else:
                    await self.log_result("Dashboard Summary", False, "Response missing required fields", data)
            else:
                await self.log_result("Dashboard Summary", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Dashboard Summary", False, f"Request failed: {str(e)}")
    
    async def test_delete_task(self):
        """Test deleting a task"""
        try:
            if not hasattr(self, 'test_task_id'):
                await self.log_result("Delete Task", False, "No test task ID available")
                return
            
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{self.test_task_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    await self.log_result("Delete Task", True, "Task deleted successfully", data)
                else:
                    await self.log_result("Delete Task", False, "Invalid response format", data)
            else:
                await self.log_result("Delete Task", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Delete Task", False, f"Request failed: {str(e)}")
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test updating non-existent task
            response = await self.client.put(
                f"{BACKEND_URL}/tasks/non-existent-id",
                headers=headers,
                json={"title": "Should fail"}
            )
            
            if response.status_code == 404:
                await self.log_result("Error Handling - Non-existent Task", True, "Correctly returned 404 for non-existent task")
            else:
                await self.log_result("Error Handling - Non-existent Task", False, f"Expected 404, got {response.status_code}")
            
            # Test deleting non-existent task
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/non-existent-id",
                headers=headers
            )
            
            if response.status_code == 404:
                await self.log_result("Error Handling - Delete Non-existent", True, "Correctly returned 404 for non-existent task deletion")
            else:
                await self.log_result("Error Handling - Delete Non-existent", False, f"Expected 404, got {response.status_code}")
                
        except Exception as e:
            await self.log_result("Error Handling", False, f"Request failed: {str(e)}")
    
    async def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive Backend Testing...")
        print("=" * 60)
        
        # Setup
        setup_success = await self.setup_mock_user()
        if not setup_success:
            print("❌ Failed to setup mock user. Aborting tests.")
            return
        
        # Run tests in logical order
        await self.test_basic_health_check()
        await self.test_auth_me_without_token()
        await self.test_auth_me_with_token()
        await self.test_create_task()
        await self.test_get_tasks()
        await self.test_get_tasks_with_filters()
        await self.test_update_task()
        await self.test_get_task_categories()
        await self.test_calendar_events()
        await self.test_dashboard_summary()
        await self.test_error_handling()
        await self.test_delete_task()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
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
    tester = BackendTester()
    passed, failed = await tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
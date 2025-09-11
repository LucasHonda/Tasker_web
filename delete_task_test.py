#!/usr/bin/env python3
"""
Focused DELETE Task Functionality Testing
Tests specifically the DELETE /api/tasks/{task_id} endpoint with comprehensive scenarios
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

class DeleteTaskTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        self.session_token = None
        self.user_id = None
        self.test_results = []
        self.created_task_ids = []
        
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
                "email": "delete.test.user@example.com",
                "name": "Delete Test User",
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
    
    async def create_test_task(self, title="Test Task for Deletion", category="Testing"):
        """Create a test task and return its ID"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            task_data = {
                "title": title,
                "description": f"Task created for delete testing - {datetime.now().isoformat()}",
                "category": category,
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
                task_id = data["id"]
                self.created_task_ids.append(task_id)
                await self.log_result("Create Test Task", True, f"Created task with ID: {task_id}")
                return task_id
            else:
                await self.log_result("Create Test Task", False, f"HTTP {response.status_code}", response.text)
                return None
                
        except Exception as e:
            await self.log_result("Create Test Task", False, f"Request failed: {str(e)}")
            return None
    
    async def test_delete_valid_task(self):
        """Test deleting a valid task that exists and belongs to the user"""
        try:
            # Create a task first
            task_id = await self.create_test_task("Task to be deleted - Valid Test")
            if not task_id:
                await self.log_result("Delete Valid Task", False, "Failed to create test task")
                return
            
            # Now delete it
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{task_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "deleted successfully" in data["message"].lower():
                    await self.log_result("Delete Valid Task", True, "Task deleted successfully", data)
                    
                    # Verify task is actually deleted by trying to fetch it
                    get_response = await self.client.get(f"{BACKEND_URL}/tasks", headers=headers)
                    if get_response.status_code == 200:
                        tasks = get_response.json()
                        deleted_task_exists = any(task["id"] == task_id for task in tasks)
                        if not deleted_task_exists:
                            await self.log_result("Verify Task Deletion", True, "Task successfully removed from database")
                        else:
                            await self.log_result("Verify Task Deletion", False, "Task still exists in database after deletion")
                else:
                    await self.log_result("Delete Valid Task", False, "Invalid response format", data)
            else:
                await self.log_result("Delete Valid Task", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Delete Valid Task", False, f"Request failed: {str(e)}")
    
    async def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            fake_task_id = str(uuid.uuid4())
            
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{fake_task_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                await self.log_result("Delete Nonexistent Task", True, "Correctly returned 404 for nonexistent task")
            else:
                await self.log_result("Delete Nonexistent Task", False, f"Expected 404, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Delete Nonexistent Task", False, f"Request failed: {str(e)}")
    
    async def test_delete_without_authentication(self):
        """Test deleting a task without authentication"""
        try:
            # Create a task first
            task_id = await self.create_test_task("Task for auth test")
            if not task_id:
                await self.log_result("Delete Without Auth", False, "Failed to create test task")
                return
            
            # Try to delete without authentication
            response = await self.client.delete(f"{BACKEND_URL}/tasks/{task_id}")
            
            if response.status_code == 401:
                await self.log_result("Delete Without Auth", True, "Correctly rejected unauthenticated delete request")
            else:
                await self.log_result("Delete Without Auth", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Delete Without Auth", False, f"Request failed: {str(e)}")
    
    async def test_delete_with_invalid_token(self):
        """Test deleting a task with invalid authentication token"""
        try:
            # Create a task first
            task_id = await self.create_test_task("Task for invalid token test")
            if not task_id:
                await self.log_result("Delete Invalid Token", False, "Failed to create test task")
                return
            
            # Try to delete with invalid token
            headers = {"Authorization": f"Bearer invalid-token-{uuid.uuid4()}"}
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{task_id}",
                headers=headers
            )
            
            if response.status_code == 401:
                await self.log_result("Delete Invalid Token", True, "Correctly rejected invalid token")
            else:
                await self.log_result("Delete Invalid Token", False, f"Expected 401, got {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Delete Invalid Token", False, f"Request failed: {str(e)}")
    
    async def test_delete_other_users_task(self):
        """Test deleting a task that belongs to another user"""
        try:
            # Create another user
            other_user_data = {
                "id": str(uuid.uuid4()),
                "email": "other.user@example.com",
                "name": "Other User",
                "picture": "https://example.com/avatar2.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.users.insert_one(other_user_data)
            
            # Create a task for the other user directly in database
            other_task = {
                "id": str(uuid.uuid4()),
                "user_id": other_user_data["id"],
                "title": "Other User's Task",
                "description": "This task belongs to another user",
                "category": "Private",
                "priority": "Medium",
                "completed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.tasks.insert_one(other_task)
            
            # Try to delete other user's task with our token
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{other_task['id']}",
                headers=headers
            )
            
            if response.status_code == 404:
                await self.log_result("Delete Other User's Task", True, "Correctly prevented deletion of other user's task (returned 404)")
            else:
                await self.log_result("Delete Other User's Task", False, f"Expected 404, got {response.status_code}", response.text)
            
            # Cleanup other user
            await self.db.users.delete_one({"id": other_user_data["id"]})
            await self.db.tasks.delete_one({"id": other_task["id"]})
                
        except Exception as e:
            await self.log_result("Delete Other User's Task", False, f"Request failed: {str(e)}")
    
    async def test_delete_multiple_tasks(self):
        """Test deleting multiple tasks in sequence"""
        try:
            # Create multiple tasks
            task_ids = []
            for i in range(3):
                task_id = await self.create_test_task(f"Bulk Delete Test Task {i+1}")
                if task_id:
                    task_ids.append(task_id)
            
            if len(task_ids) != 3:
                await self.log_result("Delete Multiple Tasks", False, "Failed to create all test tasks")
                return
            
            # Delete all tasks
            headers = {"Authorization": f"Bearer {self.session_token}"}
            deleted_count = 0
            
            for task_id in task_ids:
                response = await self.client.delete(
                    f"{BACKEND_URL}/tasks/{task_id}",
                    headers=headers
                )
                if response.status_code == 200:
                    deleted_count += 1
            
            if deleted_count == 3:
                await self.log_result("Delete Multiple Tasks", True, f"Successfully deleted {deleted_count} tasks")
            else:
                await self.log_result("Delete Multiple Tasks", False, f"Only deleted {deleted_count} out of 3 tasks")
                
        except Exception as e:
            await self.log_result("Delete Multiple Tasks", False, f"Request failed: {str(e)}")
    
    async def test_delete_completed_task(self):
        """Test deleting a completed task"""
        try:
            # Create a task
            task_id = await self.create_test_task("Task to complete and delete")
            if not task_id:
                await self.log_result("Delete Completed Task", False, "Failed to create test task")
                return
            
            # Mark it as completed
            headers = {"Authorization": f"Bearer {self.session_token}"}
            update_response = await self.client.put(
                f"{BACKEND_URL}/tasks/{task_id}",
                headers=headers,
                json={"completed": True}
            )
            
            if update_response.status_code != 200:
                await self.log_result("Delete Completed Task", False, "Failed to mark task as completed")
                return
            
            # Now delete the completed task
            delete_response = await self.client.delete(
                f"{BACKEND_URL}/tasks/{task_id}",
                headers=headers
            )
            
            if delete_response.status_code == 200:
                data = delete_response.json()
                if "message" in data and "deleted successfully" in data["message"].lower():
                    await self.log_result("Delete Completed Task", True, "Successfully deleted completed task", data)
                else:
                    await self.log_result("Delete Completed Task", False, "Invalid response format", data)
            else:
                await self.log_result("Delete Completed Task", False, f"HTTP {delete_response.status_code}", delete_response.text)
                
        except Exception as e:
            await self.log_result("Delete Completed Task", False, f"Request failed: {str(e)}")
    
    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            # Remove test user
            if self.user_id:
                await self.db.users.delete_one({"id": self.user_id})
            
            # Remove any remaining test tasks
            if self.user_id:
                await self.db.tasks.delete_many({"user_id": self.user_id})
            
            # Remove any tasks we created by ID
            for task_id in self.created_task_ids:
                await self.db.tasks.delete_one({"id": task_id})
            
            await self.log_result("Cleanup Test Data", True, "Test data cleaned up successfully")
            
        except Exception as e:
            await self.log_result("Cleanup Test Data", False, f"Failed to cleanup: {str(e)}")
    
    async def run_delete_tests(self):
        """Run all delete-specific tests"""
        print("🗑️  Starting DELETE Task Functionality Testing...")
        print("=" * 60)
        
        # Setup
        setup_success = await self.setup_mock_user()
        if not setup_success:
            print("❌ Failed to setup mock user. Aborting tests.")
            return
        
        # Run delete-specific tests
        await self.test_delete_valid_task()
        await self.test_delete_nonexistent_task()
        await self.test_delete_without_authentication()
        await self.test_delete_with_invalid_token()
        await self.test_delete_other_users_task()
        await self.test_delete_multiple_tasks()
        await self.test_delete_completed_task()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 DELETE FUNCTIONALITY TEST SUMMARY")
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
        else:
            print("\n🎉 ALL DELETE FUNCTIONALITY TESTS PASSED!")
            print("The DELETE /api/tasks/{task_id} endpoint is working correctly.")
        
        print("\n" + "=" * 60)
        
        # Close connections
        await self.client.aclose()
        self.mongo_client.close()
        
        return passed, failed

async def main():
    """Main test runner"""
    tester = DeleteTaskTester()
    passed, failed = await tester.run_delete_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Additional Backend Testing for Edge Cases and Advanced Features
"""

import asyncio
import httpx
import json
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Configuration
BACKEND_URL = "https://schedule-buddy-62.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

class AdditionalBackendTester:
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
        """Create a mock user session for testing"""
        try:
            user_data = {
                "id": str(uuid.uuid4()),
                "email": "advanced.test@example.com",
                "name": "Advanced Test User",
                "picture": "https://example.com/avatar.jpg",
                "session_token": str(uuid.uuid4()),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.users.insert_one(user_data)
            self.session_token = user_data["session_token"]
            self.user_id = user_data["id"]
            
            await self.log_result("Setup Mock User", True, "Mock user created successfully")
            return True
            
        except Exception as e:
            await self.log_result("Setup Mock User", False, f"Failed to create mock user: {str(e)}")
            return False
    
    async def test_task_validation(self):
        """Test task creation with invalid data"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test empty title
            response = await self.client.post(
                f"{BACKEND_URL}/tasks",
                headers=headers,
                json={"title": "", "description": "Empty title test"}
            )
            
            if response.status_code == 422:
                await self.log_result("Task Validation - Empty Title", True, "Correctly rejected empty title")
            else:
                await self.log_result("Task Validation - Empty Title", False, f"Expected 422, got {response.status_code}")
            
            # Test missing title
            response = await self.client.post(
                f"{BACKEND_URL}/tasks",
                headers=headers,
                json={"description": "Missing title test"}
            )
            
            if response.status_code == 422:
                await self.log_result("Task Validation - Missing Title", True, "Correctly rejected missing title")
            else:
                await self.log_result("Task Validation - Missing Title", False, f"Expected 422, got {response.status_code}")
                
        except Exception as e:
            await self.log_result("Task Validation", False, f"Request failed: {str(e)}")
    
    async def test_multiple_tasks_with_categories(self):
        """Test creating multiple tasks with different categories and priorities"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            tasks_data = [
                {
                    "title": "High Priority Work Task",
                    "category": "Work",
                    "priority": "High",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                },
                {
                    "title": "Medium Priority Personal Task",
                    "category": "Personal",
                    "priority": "Medium",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
                },
                {
                    "title": "Low Priority Shopping Task",
                    "category": "Shopping",
                    "priority": "Low",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                }
            ]
            
            created_tasks = []
            for i, task_data in enumerate(tasks_data):
                response = await self.client.post(
                    f"{BACKEND_URL}/tasks",
                    headers=headers,
                    json=task_data
                )
                
                if response.status_code == 200:
                    created_tasks.append(response.json())
                else:
                    await self.log_result(f"Create Multiple Tasks - Task {i+1}", False, f"HTTP {response.status_code}")
                    return
            
            await self.log_result("Create Multiple Tasks", True, f"Created {len(created_tasks)} tasks successfully")
            
            # Test filtering by each category
            for category in ["Work", "Personal", "Shopping"]:
                response = await self.client.get(
                    f"{BACKEND_URL}/tasks?category={category}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    if len(tasks) >= 1 and all(task["category"] == category for task in tasks):
                        await self.log_result(f"Filter by Category - {category}", True, f"Found {len(tasks)} tasks in {category}")
                    else:
                        await self.log_result(f"Filter by Category - {category}", False, f"Filtering failed for {category}")
                else:
                    await self.log_result(f"Filter by Category - {category}", False, f"HTTP {response.status_code}")
            
            # Store task IDs for cleanup
            self.created_task_ids = [task["id"] for task in created_tasks]
                
        except Exception as e:
            await self.log_result("Multiple Tasks with Categories", False, f"Request failed: {str(e)}")
    
    async def test_dashboard_with_data(self):
        """Test dashboard summary with actual task data"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            response = await self.client.get(f"{BACKEND_URL}/dashboard/summary", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                task_stats = data["task_stats"]
                
                # Should have at least 3 tasks from previous test
                if task_stats["total"] >= 3:
                    await self.log_result("Dashboard with Data", True, f"Dashboard shows {task_stats['total']} total tasks", data)
                else:
                    await self.log_result("Dashboard with Data", False, f"Expected at least 3 tasks, got {task_stats['total']}", data)
            else:
                await self.log_result("Dashboard with Data", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("Dashboard with Data", False, f"Request failed: {str(e)}")
    
    async def test_task_completion_workflow(self):
        """Test marking tasks as completed and filtering"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            if not hasattr(self, 'created_task_ids') or not self.created_task_ids:
                await self.log_result("Task Completion Workflow", False, "No task IDs available")
                return
            
            # Mark first task as completed
            task_id = self.created_task_ids[0]
            response = await self.client.put(
                f"{BACKEND_URL}/tasks/{task_id}",
                headers=headers,
                json={"completed": True}
            )
            
            if response.status_code == 200:
                # Test filtering completed tasks
                response = await self.client.get(
                    f"{BACKEND_URL}/tasks?completed=true",
                    headers=headers
                )
                
                if response.status_code == 200:
                    completed_tasks = response.json()
                    if len(completed_tasks) >= 1:
                        await self.log_result("Task Completion Workflow", True, f"Found {len(completed_tasks)} completed tasks")
                    else:
                        await self.log_result("Task Completion Workflow", False, "No completed tasks found after marking one as completed")
                else:
                    await self.log_result("Task Completion Workflow", False, f"Failed to get completed tasks: HTTP {response.status_code}")
            else:
                await self.log_result("Task Completion Workflow", False, f"Failed to mark task as completed: HTTP {response.status_code}")
                
        except Exception as e:
            await self.log_result("Task Completion Workflow", False, f"Request failed: {str(e)}")
    
    async def test_date_time_handling(self):
        """Test datetime handling in tasks"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Create task with specific datetime
            future_date = datetime.now(timezone.utc) + timedelta(days=5, hours=14, minutes=30)
            reminder_date = datetime.now(timezone.utc) + timedelta(days=4, hours=9)
            
            task_data = {
                "title": "DateTime Test Task",
                "description": "Testing datetime handling",
                "due_date": future_date.isoformat(),
                "reminder": reminder_date.isoformat()
            }
            
            response = await self.client.post(
                f"{BACKEND_URL}/tasks",
                headers=headers,
                json=task_data
            )
            
            if response.status_code == 200:
                created_task = response.json()
                
                # Verify dates are preserved correctly
                if "due_date" in created_task and "reminder" in created_task:
                    await self.log_result("DateTime Handling", True, "DateTime fields preserved correctly", {
                        "due_date": created_task["due_date"],
                        "reminder": created_task["reminder"]
                    })
                    
                    # Store for cleanup
                    if not hasattr(self, 'created_task_ids'):
                        self.created_task_ids = []
                    self.created_task_ids.append(created_task["id"])
                else:
                    await self.log_result("DateTime Handling", False, "DateTime fields missing in response", created_task)
            else:
                await self.log_result("DateTime Handling", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            await self.log_result("DateTime Handling", False, f"Request failed: {str(e)}")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
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
    
    async def run_all_tests(self):
        """Run all additional tests"""
        print("🔬 Starting Additional Backend Testing...")
        print("=" * 60)
        
        # Setup
        setup_success = await self.setup_mock_user()
        if not setup_success:
            print("❌ Failed to setup mock user. Aborting tests.")
            return
        
        # Run additional tests
        await self.test_task_validation()
        await self.test_multiple_tasks_with_categories()
        await self.test_dashboard_with_data()
        await self.test_task_completion_workflow()
        await self.test_date_time_handling()
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 ADDITIONAL TEST SUMMARY")
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
    tester = AdditionalBackendTester()
    passed, failed = await tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Cookie
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Calendar & Task Manager", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Authentication Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str

# Task Models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "General"
    priority: Optional[str] = "Medium"  # Low, Medium, High
    due_date: Optional[datetime] = None
    reminder: Optional[datetime] = None
    completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "General"
    priority: Optional[str] = "Medium"
    due_date: Optional[datetime] = None
    reminder: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder: Optional[datetime] = None
    completed: Optional[bool] = None

# Calendar Event Models
class CalendarEvent(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = ""
    calendar_id: str

# Authentication Helper Functions
async def get_current_user(
    request: Request,
    authorization: Optional[str] = Cookie(None, alias="session_token")
) -> UserSession:
    session_token = authorization
    
    # Fallback to Authorization header if cookie not present
    if not session_token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Find user by session token
    user_doc = await db.users.find_one({"session_token": session_token})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    # Check if session is expired
    if user_doc["expires_at"] < datetime.now(timezone.utc):
        # Remove expired session
        await db.users.delete_one({"session_token": session_token})
        raise HTTPException(status_code=401, detail="Session expired")
    
    return UserSession(
        user_id=user_doc["id"],
        email=user_doc["email"],
        name=user_doc["name"],
        picture=user_doc["picture"]
    )

async def get_google_calendar_service(current_user: UserSession = Depends(get_current_user)):
    """Get authenticated Google Calendar service for the current user"""
    try:
        # Get user's stored session token
        user_doc = await db.users.find_one({"id": current_user.user_id})
        if not user_doc or not user_doc.get("session_token"):
            raise HTTPException(status_code=401, detail="No valid session found")
        
        # Get additional OAuth info from Emergent Auth system
        session_token = user_doc["session_token"]
        
        # Call Emergent Auth to get Google OAuth token details
        async with httpx.AsyncClient() as client:
            try:
                # Try to get extended session data that might include Google OAuth tokens
                response = await client.get(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/google-calendar-access",
                    headers={"X-Session-Token": session_token},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    google_data = response.json()
                    return {"google_oauth_data": google_data, "user_email": current_user.email}
                else:
                    # If specific calendar endpoint doesn't exist, try general approach
                    logging.info(f"Calendar-specific endpoint returned {response.status_code}, using mock data")
                    return {"user_email": current_user.email, "authenticated": True, "use_mock": True}
                    
            except httpx.TimeoutException:
                logging.warning("Timeout getting Google Calendar access, using mock data")
                return {"user_email": current_user.email, "authenticated": True, "use_mock": True}
            except Exception as e:
                logging.warning(f"Error getting Google Calendar access: {str(e)}, using mock data")
                return {"user_email": current_user.email, "authenticated": True, "use_mock": True}
        
    except Exception as e:
        logging.error(f"Failed to get Google Calendar service: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to access calendar service")

# Basic Routes
@api_router.get("/")
async def root():
    return {"message": "Calendar & Task Manager API"}

# Authentication Routes
@api_router.post("/auth/session")
async def process_session(request: Request, response: Response):
    """Process session_id from Emergent Auth and create user session"""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Call Emergent Auth to get user data
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid session ID")
            
            user_data = auth_response.json()
        
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data["email"]})
        
        if existing_user:
            # Update session token and expiry
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            await db.users.update_one(
                {"email": user_data["email"]},
                {
                    "$set": {
                        "session_token": user_data["session_token"],
                        "expires_at": expires_at
                    }
                }
            )
            user_id = existing_user["id"]
        else:
            # Create new user
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            user = User(
                id=str(uuid.uuid4()),
                email=user_data["email"],
                name=user_data["name"],
                picture=user_data["picture"],
                session_token=user_data["session_token"],
                expires_at=expires_at
            )
            await db.users.insert_one(user.dict())
            user_id = user.id
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=user_data["session_token"],
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return {
            "user_id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data["picture"]
        }
        
    except Exception as e:
        logging.error(f"Session processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Session processing failed")

@api_router.post("/auth/logout")
async def logout(response: Response, current_user: UserSession = Depends(get_current_user)):
    """Logout user and clear session"""
    # Remove session from database
    await db.users.delete_one({"id": current_user.user_id})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: UserSession = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Task Management Routes
@api_router.post("/tasks", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    current_user: UserSession = Depends(get_current_user)
):
    """Create a new task"""
    task = Task(
        user_id=current_user.user_id,
        **task_data.dict()
    )
    
    task_dict = task.dict()
    # Convert datetime objects to ISO strings for MongoDB
    if task_dict.get('due_date'):
        task_dict['due_date'] = task_dict['due_date'].isoformat()
    if task_dict.get('reminder'):
        task_dict['reminder'] = task_dict['reminder'].isoformat()
    task_dict['created_at'] = task_dict['created_at'].isoformat()
    task_dict['updated_at'] = task_dict['updated_at'].isoformat()
    
    await db.tasks.insert_one(task_dict)
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(
    category: Optional[str] = None,
    completed: Optional[bool] = None,
    current_user: UserSession = Depends(get_current_user)
):
    """Get tasks for current user"""
    query = {"user_id": current_user.user_id}
    
    if category:
        query["category"] = category
    if completed is not None:
        query["completed"] = completed
    
    tasks = await db.tasks.find(query).sort("created_at", -1).to_list(1000)
    
    # Convert ISO strings back to datetime objects
    for task in tasks:
        if task.get('due_date'):
            task['due_date'] = datetime.fromisoformat(task['due_date'])
        if task.get('reminder'):
            task['reminder'] = datetime.fromisoformat(task['reminder'])
        task['created_at'] = datetime.fromisoformat(task['created_at'])
        task['updated_at'] = datetime.fromisoformat(task['updated_at'])
    
    return [Task(**task) for task in tasks]

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: UserSession = Depends(get_current_user)
):
    """Update a task"""
    # Check if task exists and belongs to user
    existing_task = await db.tasks.find_one({"id": task_id, "user_id": current_user.user_id})
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Prepare update data
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Convert datetime objects to ISO strings
        if 'due_date' in update_data and update_data['due_date']:
            update_data['due_date'] = update_data['due_date'].isoformat()
        if 'reminder' in update_data and update_data['reminder']:
            update_data['reminder'] = update_data['reminder'].isoformat()
        
        await db.tasks.update_one(
            {"id": task_id, "user_id": current_user.user_id},
            {"$set": update_data}
        )
    
    # Get updated task
    updated_task = await db.tasks.find_one({"id": task_id})
    
    # Convert ISO strings back to datetime objects
    if updated_task.get('due_date'):
        updated_task['due_date'] = datetime.fromisoformat(updated_task['due_date'])
    if updated_task.get('reminder'):
        updated_task['reminder'] = datetime.fromisoformat(updated_task['reminder'])
    updated_task['created_at'] = datetime.fromisoformat(updated_task['created_at'])
    updated_task['updated_at'] = datetime.fromisoformat(updated_task['updated_at'])
    
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: UserSession = Depends(get_current_user)
):
    """Delete a task"""
    result = await db.tasks.delete_one({"id": task_id, "user_id": current_user.user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}

@api_router.get("/tasks/categories")
async def get_task_categories(current_user: UserSession = Depends(get_current_user)):
    """Get all unique categories for user's tasks"""
    pipeline = [
        {"$match": {"user_id": current_user.user_id}},
        {"$group": {"_id": "$category"}},
        {"$sort": {"_id": 1}}
    ]
    
    categories = await db.tasks.aggregate(pipeline).to_list(100)
    return [cat["_id"] for cat in categories if cat["_id"]]

# Calendar Routes
@api_router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    calendar_service = Depends(get_google_calendar_service),
    current_user: UserSession = Depends(get_current_user)
):
    """Get calendar events - Enhanced mock data with user context"""
    
    # Parse date range if provided
    start_dt = datetime.now(timezone.utc) - timedelta(days=1)  # Default: yesterday
    end_dt = datetime.now(timezone.utc) + timedelta(days=30)   # Default: next 30 days
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    # Enhanced mock events with more variety and user context
    mock_events = [
        {
            "id": "event_1",
            "title": f"Welcome Meeting - {current_user.name}",
            "description": "Onboarding session and goal setting",
            "start_time": datetime.now(timezone.utc) + timedelta(hours=2),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=3),
            "all_day": False,
            "location": "Conference Room A",
            "calendar_id": "primary"
        },
        {
            "id": "event_2",
            "title": "Project Planning Session",
            "description": "Quarterly planning and resource allocation",
            "start_time": datetime.now(timezone.utc) + timedelta(days=1, hours=10),
            "end_time": datetime.now(timezone.utc) + timedelta(days=1, hours=12),
            "all_day": False,
            "location": "Meeting Room B",
            "calendar_id": "primary"
        },
        {
            "id": "event_3",
            "title": "All Hands Meeting",
            "description": "Company-wide updates and announcements",
            "start_time": datetime.now(timezone.utc) + timedelta(days=3),
            "end_time": datetime.now(timezone.utc) + timedelta(days=3, hours=1),
            "all_day": True,
            "location": "Main Auditorium",
            "calendar_id": "primary"
        },
        {
            "id": "event_4",
            "title": "Client Presentation",
            "description": "Present project proposal and deliverables",
            "start_time": datetime.now(timezone.utc) + timedelta(days=5, hours=14),
            "end_time": datetime.now(timezone.utc) + timedelta(days=5, hours=15, minutes=30),
            "all_day": False,
            "location": "Client Office - Downtown",
            "calendar_id": "primary"
        },
        {
            "id": "event_5",
            "title": "Team Building Workshop",
            "description": "Interactive team building and collaboration exercises",
            "start_time": datetime.now(timezone.utc) + timedelta(days=8, hours=9),
            "end_time": datetime.now(timezone.utc) + timedelta(days=8, hours=17),
            "all_day": False,
            "location": "Offsite Location",
            "calendar_id": "primary"
        },
        {
            "id": "event_6",
            "title": "Performance Review",
            "description": f"Quarterly review session with {current_user.name}",
            "start_time": datetime.now(timezone.utc) + timedelta(days=10, hours=15),
            "end_time": datetime.now(timezone.utc) + timedelta(days=10, hours=16),
            "all_day": False,
            "location": "Manager's Office",
            "calendar_id": "primary"
        },
        {
            "id": "event_7",
            "title": "Training Workshop",
            "description": "Professional development and skill enhancement",
            "start_time": datetime.now(timezone.utc) + timedelta(days=12, hours=13),
            "end_time": datetime.now(timezone.utc) + timedelta(days=12, hours=17),
            "all_day": False,
            "location": "Training Center",
            "calendar_id": "primary"
        },
        {
            "id": "event_8",
            "title": "Monthly Standup",
            "description": "Progress updates and roadmap discussion",
            "start_time": datetime.now(timezone.utc) + timedelta(days=15, hours=10),
            "end_time": datetime.now(timezone.utc) + timedelta(days=15, hours=11),
            "all_day": False,
            "location": "Virtual Meeting",
            "calendar_id": "primary"
        }
    ]
    
    # Filter events by date range
    filtered_events = []
    for event in mock_events:
        event_start = event["start_time"]
        if start_dt <= event_start <= end_dt:
            filtered_events.append(event)
    
    return [CalendarEvent(**event) for event in filtered_events]

# Dashboard/Summary Routes
@api_router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: UserSession = Depends(get_current_user),
    calendar_service = Depends(get_google_calendar_service)
):
    """Get dashboard summary with tasks and events overview"""
    
    # Get task statistics
    total_tasks = await db.tasks.count_documents({"user_id": current_user.user_id})
    completed_tasks = await db.tasks.count_documents({"user_id": current_user.user_id, "completed": True})
    pending_tasks = total_tasks - completed_tasks
    
    # Get today's tasks
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    today_tasks = await db.tasks.find({
        "user_id": current_user.user_id,
        "due_date": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    }).to_list(100)
    
    # Get upcoming tasks (next 7 days)
    week_end = today_start + timedelta(days=7)
    upcoming_tasks = await db.tasks.find({
        "user_id": current_user.user_id,
        "due_date": {"$gte": today_start.isoformat(), "$lt": week_end.isoformat()},
        "completed": False
    }).to_list(100)
    
    # Get upcoming events count (enhanced mock data)
    # In reality, this would count actual calendar events from Google Calendar API
    upcoming_events_count = 8  # Based on our enhanced mock data
    
    return {
        "task_stats": {
            "total": total_tasks,
            "completed": completed_tasks,
            "pending": pending_tasks
        },
        "today_tasks_count": len(today_tasks),
        "upcoming_tasks_count": len(upcoming_tasks),
        "upcoming_events_count": upcoming_events_count,
        "user_info": {
            "name": current_user.name,
            "email": current_user.email,
            "calendar_connected": True  # Since we have mock calendar integration
        }
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
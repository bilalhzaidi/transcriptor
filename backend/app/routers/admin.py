from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.models.schemas import SystemStats, AdminDashboardResponse
from app.services.auth import require_admin
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(admin: dict = Depends(require_admin)):
    """Get admin dashboard statistics"""
    
    # Mock system stats
    stats = SystemStats(
        total_users=12847,
        active_users=8934,
        total_transcriptions=45623,
        monthly_revenue=89450.0,
        system_uptime=99.9,
        avg_processing_time=2.3
    )
    
    # Mock recent activity
    recent_activity = [
        {
            "id": 1,
            "user": "john@example.com",
            "action": "Upgraded to Pro",
            "time": "2 minutes ago",
            "type": "upgrade"
        },
        {
            "id": 2,
            "user": "sarah@company.com",
            "action": "Transcribed 45min video",
            "time": "5 minutes ago",
            "type": "transcription"
        },
        {
            "id": 3,
            "user": "mike@startup.io",
            "action": "API key generated",
            "time": "8 minutes ago",
            "type": "api"
        },
        {
            "id": 4,
            "user": "lisa@agency.com",
            "action": "Cancelled subscription",
            "time": "12 minutes ago",
            "type": "cancellation"
        },
        {
            "id": 5,
            "user": "david@corp.com",
            "action": "Bulk upload completed",
            "time": "15 minutes ago",
            "type": "upload"
        }
    ]
    
    # Mock system health
    system_health = [
        {"service": "API Gateway", "status": "healthy", "uptime": 99.9},
        {"service": "Transcription Engine", "status": "healthy", "uptime": 99.8},
        {"service": "File Storage", "status": "healthy", "uptime": 100.0},
        {"service": "Database", "status": "warning", "uptime": 98.5},
        {"service": "Authentication", "status": "healthy", "uptime": 99.9}
    ]
    
    return AdminDashboardResponse(
        stats=stats,
        recent_activity=recent_activity,
        system_health=system_health
    )

@router.get("/users")
async def get_users(
    page: int = 1,
    limit: int = 50,
    search: str = None,
    admin: dict = Depends(require_admin)
):
    """Get paginated list of users"""
    
    # Mock user data
    mock_users = [
        {
            "id": f"user_{i}",
            "email": f"user{i}@example.com",
            "display_name": f"User {i}",
            "subscription_plan": "basic" if i % 3 == 0 else "trial",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat(),
            "is_active": True,
            "total_transcriptions": i * 5,
            "total_minutes": i * 120
        }
        for i in range(1, 101)
    ]
    
    # Apply search filter if provided
    if search:
        mock_users = [
            user for user in mock_users 
            if search.lower() in user["email"].lower() or search.lower() in user["display_name"].lower()
        ]
    
    # Apply pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_users = mock_users[start_idx:end_idx]
    
    return {
        "users": paginated_users,
        "total": len(mock_users),
        "page": page,
        "limit": limit,
        "total_pages": (len(mock_users) + limit - 1) // limit
    }

@router.put("/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: str,
    plan_id: str,
    extend_days: int = None,
    admin: dict = Depends(require_admin)
):
    """Update user subscription"""
    
    logger.info(f"Admin {admin['email']} updating subscription for user {user_id} to plan {plan_id}")
    
    # Mock response
    return {
        "message": f"User {user_id} subscription updated to {plan_id}",
        "user_id": user_id,
        "new_plan": plan_id,
        "extended_days": extend_days
    }

@router.get("/analytics/revenue")
async def get_revenue_analytics(
    period: str = "monthly",
    admin: dict = Depends(require_admin)
):
    """Get revenue analytics"""
    
    # Mock revenue data
    if period == "monthly":
        return {
            "period": "monthly",
            "data": [
                {"month": "Jan", "revenue": 65000, "users": 1200},
                {"month": "Feb", "revenue": 72000, "users": 1350},
                {"month": "Mar", "revenue": 78000, "users": 1480},
                {"month": "Apr", "revenue": 81000, "users": 1620},
                {"month": "May", "revenue": 85000, "users": 1750},
                {"month": "Jun", "revenue": 89450, "users": 1890}
            ]
        }
    else:
        return {
            "period": "daily",
            "data": [
                {"date": "2024-01-01", "revenue": 2800, "users": 45},
                {"date": "2024-01-02", "revenue": 3200, "users": 52},
                {"date": "2024-01-03", "revenue": 2900, "users": 48}
            ]
        }

@router.get("/analytics/usage")
async def get_usage_analytics(admin: dict = Depends(require_admin)):
    """Get usage analytics"""
    
    return {
        "content_types": [
            {"name": "Audio Files", "value": 65, "color": "#3B82F6"},
            {"name": "Video Files", "value": 25, "color": "#8B5CF6"},
            {"name": "YouTube URLs", "value": 10, "color": "#10B981"}
        ],
        "languages": [
            {"language": "English", "count": 28450},
            {"language": "Spanish", "count": 8920},
            {"language": "French", "count": 4560},
            {"language": "German", "count": 2890},
            {"language": "Other", "count": 1803}
        ],
        "processing_times": {
            "average": 2.3,
            "median": 1.8,
            "p95": 5.2,
            "p99": 12.1
        }
    }

@router.get("/system/health")
async def get_system_health(admin: dict = Depends(require_admin)):
    """Get detailed system health information"""
    
    return {
        "services": [
            {
                "name": "API Gateway",
                "status": "healthy",
                "uptime": 99.9,
                "response_time": 45,
                "last_check": datetime.utcnow().isoformat()
            },
            {
                "name": "Transcription Engine",
                "status": "healthy", 
                "uptime": 99.8,
                "response_time": 1200,
                "last_check": datetime.utcnow().isoformat()
            },
            {
                "name": "File Storage",
                "status": "healthy",
                "uptime": 100.0,
                "response_time": 25,
                "last_check": datetime.utcnow().isoformat()
            },
            {
                "name": "Database",
                "status": "warning",
                "uptime": 98.5,
                "response_time": 85,
                "last_check": datetime.utcnow().isoformat(),
                "issues": ["High connection count", "Slow query detected"]
            }
        ],
        "metrics": {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 34.1,
            "network_io": 1250.5
        }
    }
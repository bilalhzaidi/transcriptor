from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.models.schemas import UserProfile, User, Subscription, SubscriptionStatus, UsageStats
from app.services.auth import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock data for development
MOCK_SUBSCRIPTION_PLANS = {
    "trial": {
        "id": "trial",
        "name": "Free Trial",
        "max_file_size_mb": 25,
        "max_monthly_minutes": 30,
        "max_concurrent_tasks": 1
    },
    "basic": {
        "id": "basic", 
        "name": "Basic",
        "max_file_size_mb": 100,
        "max_monthly_minutes": 300,
        "max_concurrent_tasks": 2
    },
    "pro": {
        "id": "pro",
        "name": "Pro", 
        "max_file_size_mb": 500,
        "max_monthly_minutes": 1500,
        "max_concurrent_tasks": 5
    }
}

@router.post("/verify-token")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify Firebase token and return user profile"""
    
    try:
        # Create mock user profile
        mock_user = User(
            id=user['uid'],
            email=user['email'],
            display_name=user.get('name', 'User'),
            subscription_id="trial",
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
            is_active=True,
            is_admin=user['email'] in ['admin@transcriptor.ai', 'admin@example.com']
        )
        
        # Create mock subscription
        mock_subscription = Subscription(
            id="sub_trial_123",
            user_id=user['uid'],
            plan_id="trial",
            status=SubscriptionStatus.TRIAL,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            auto_renew=False
        )
        
        # Create mock usage stats
        mock_usage = UsageStats(
            current_period={
                "files_processed": 5,
                "minutes_transcribed": 150,
                "translations_used": 2
            },
            limits={
                "max_file_size_mb": 25,
                "max_monthly_minutes": 1800,
                "max_concurrent_tasks": 1
            },
            remaining={
                "minutes": 1650,
                "files": 95
            }
        )
        
        return UserProfile(
            user=mock_user,
            subscription=mock_subscription,
            usage=mock_usage
        )
        
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )

@router.get("/user/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """Get user profile with subscription and usage info"""
    
    # Mock user profile data
    mock_user = User(
        id=user['uid'],
        email=user['email'],
        display_name=user.get('name', 'User'),
        subscription_id="trial",
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
        is_active=True,
        is_admin=user['email'] in ['admin@transcriptor.ai', 'admin@example.com']
    )
    
    mock_subscription = Subscription(
        id="sub_trial_123",
        user_id=user['uid'],
        plan_id="trial",
        status=SubscriptionStatus.TRIAL,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
        auto_renew=False
    )
    
    mock_usage = UsageStats(
        current_period={
            "files_processed": 5,
            "minutes_transcribed": 150,
            "translations_used": 2
        },
        limits={
            "max_file_size_mb": 25,
            "max_monthly_minutes": 1800,
            "max_concurrent_tasks": 1
        },
        remaining={
            "minutes": 1650,
            "files": 95
        }
    )
    
    return UserProfile(
        user=mock_user,
        subscription=mock_subscription,
        usage=mock_usage
    )

@router.put("/user/profile")
async def update_user_profile(
    display_name: str,
    user: dict = Depends(get_current_user)
):
    """Update user profile"""
    
    # In a real implementation, you would update the database
    logger.info(f"Updating profile for user {user['uid']}: display_name={display_name}")
    
    # Return updated user
    updated_user = User(
        id=user['uid'],
        email=user['email'],
        display_name=display_name,
        subscription_id="trial",
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
        is_active=True,
        is_admin=user['email'] in ['admin@transcriptor.ai', 'admin@example.com']
    )
    
    return {"user": updated_user}

@router.get("/usage/current")
async def get_current_usage(user: dict = Depends(get_current_user)):
    """Get current usage statistics"""
    
    # Mock usage data
    return UsageStats(
        current_period={
            "files_processed": 12,
            "minutes_transcribed": 450,
            "translations_used": 8
        },
        limits={
            "max_file_size_mb": 100,
            "max_monthly_minutes": 1800,
            "max_concurrent_tasks": 2
        },
        remaining={
            "minutes": 1350,
            "files": 88
        }
    )
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        logger.info("Firebase Admin SDK already initialized")
    except ValueError:
        # Initialize Firebase Admin SDK
        firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if firebase_credentials_path and os.path.exists(firebase_credentials_path):
            cred = credentials.Certificate(firebase_credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with credentials file")
        else:
            # For development, you can use default credentials
            logger.warning("Firebase credentials not found, using default initialization")
            firebase_admin.initialize_app()

# Security scheme
security = HTTPBearer()

class AuthService:
    def __init__(self):
        initialize_firebase()
    
    async def verify_token(self, token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            decoded_token = auth.verify_id_token(token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'email_verified': decoded_token.get('email_verified', False)
            }
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """Get current authenticated user"""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        return await self.verify_token(credentials.credentials)
    
    async def get_current_user_optional(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
        """Get current user if authenticated, otherwise return None"""
        if not credentials:
            return None
        
        try:
            return await self.verify_token(credentials.credentials)
        except HTTPException:
            return None
    
    async def require_admin(self, user: dict = Depends(get_current_user)) -> dict:
        """Require admin role"""
        # In a real implementation, you would check the user's role from your database
        # For now, we'll check if the user email is in an admin list
        admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
        if user.get('email') not in admin_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return user

# Create global auth service instance
auth_service = AuthService()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return await auth_service.get_current_user(credentials)

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    return await auth_service.get_current_user_optional(credentials)

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    return await auth_service.require_admin(user)
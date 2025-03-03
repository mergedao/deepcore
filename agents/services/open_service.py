import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import OpenPlatformKey


def generate_key_pair():
    """Generate a new access key and secret key pair for open platform"""
    access_key = f"ak_{uuid.uuid4().hex[:16]}"
    secret_key = f"sk_{uuid.uuid4().hex}"
    return access_key, secret_key

def generate_signature(access_key: str, secret_key: str, timestamp: str) -> str:
    """Generate signature for open platform API request"""
    message = f"{access_key}{timestamp}"
    return hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_signature(access_key: str, secret_key: str, timestamp: str, signature: str) -> bool:
    """Verify open platform API signature"""
    expected_signature = generate_signature(access_key, secret_key, timestamp)
    return hmac.compare_digest(signature, expected_signature)

async def get_or_create_credentials(user: dict, session: AsyncSession) -> dict:
    """Get existing credentials or create new ones if they don't exist"""
    user_id = user.get("user_id")
    if not user_id:
        raise CustomAgentException(
            error_code=ErrorCode.INVALID_REQUEST,
            message="User ID is required"
        )

    # Try to get existing credentials
    query = select(OpenPlatformKey).where(
        OpenPlatformKey.user_id == user_id,
        OpenPlatformKey.is_deleted == False
    )
    result = await session.execute(query)
    credentials = result.scalar_one_or_none()
    
    if credentials:
        return {
            "access_key": credentials.access_key,
            "secret_key": credentials.secret_key
        }
    
    # Create new credentials if none exist
    access_key, secret_key = generate_key_pair()
    credentials = OpenPlatformKey(
        name=f"User {user_id} Open Platform Key",
        access_key=access_key,
        secret_key=secret_key,
        user_id=user_id,
        created_at=datetime.utcnow()
    )
    
    session.add(credentials)
    await session.commit()
    
    return {
        "access_key": access_key,
        "secret_key": secret_key
    }

async def get_credentials(access_key: str, session: AsyncSession) -> Optional[OpenPlatformKey]:
    """Get credentials by access key"""
    query = select(OpenPlatformKey).where(
        OpenPlatformKey.access_key == access_key,
        OpenPlatformKey.is_deleted == False
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() 

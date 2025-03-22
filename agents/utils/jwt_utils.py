import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import jwt

from agents.common.config import SETTINGS

# JWT configuration
JWT_SECRET = SETTINGS.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(days=SETTINGS.JWT_EXPIRATION_TIME)

# Access token expires in 30 days
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 * 30
# Refresh token expires in 60 days
REFRESH_TOKEN_EXPIRE_DAYS = 60

logger = logging.getLogger(__name__)


def generate_token(user_id: int, username: str, tenant_id: str) -> str:
    """
    Generate JWT token with user information including tenant_id
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'tenant_id': tenant_id,
        'exp': datetime.utcnow() + JWT_EXPIRATION_DELTA
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and return payload if valid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.error("Token is expired", e, exc_info=True)
        return None
    except jwt.InvalidTokenError as e:
        logger.error("Invalid token", e, exc_info=True)
        return None

def generate_token_pair(user_id: str, username: str, tenant_id: str, wallet_address: str = None, chain_type: str = None) -> Tuple[str, str]:
    """
    Generate a pair of tokens (access token and refresh token)
    :param user_id: User ID
    :param username: Username
    :param tenant_id: Tenant ID
    :param wallet_address: Wallet address
    :param chain_type: Blockchain type
    :return: Tuple of access token and refresh token
    """
    access_token = generate_access_token(user_id, username, tenant_id, wallet_address, chain_type)
    refresh_token = generate_refresh_token(user_id)
    return access_token, refresh_token

def generate_access_token(user_id: str, username: str, tenant_id: str, wallet_address: str = None, chain_type: str = None) -> str:
    """
    Generate a short-lived JWT token containing user information
    :param user_id: User ID
    :param username: Username
    :param tenant_id: Tenant ID
    :param wallet_address: Wallet address
    :param chain_type: Blockchain type
    :return: JWT token
    """
    payload = {
        "user_id": user_id,
        "username": username,
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    
    if wallet_address:
        payload["wallet_address"] = wallet_address
        
    if chain_type:
        payload["chain_type"] = chain_type
        
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_refresh_token(user_id: str) -> str:
    """
    Generate refresh token with just user_id and long expiry
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "user_id": user_id,
        "token_type": "refresh"
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_refresh_token(refresh_token: str) -> Optional[str]:
    """
    Verify refresh token and return user_id if valid
    """
    try:
        payload = jwt.decode(
            refresh_token, 
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        if payload.get("token_type") != "refresh":
            return None
        return payload.get("user_id")
    except jwt.PyJWTError:
        return None

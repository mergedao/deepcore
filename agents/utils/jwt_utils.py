import logging

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional

from agents.common.config import SETTINGS

# JWT configuration
JWT_SECRET = SETTINGS.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(days=1)

logger = logging.getLogger(__name__)


def generate_token(user_id: int, username: str, tenant_id: str) -> str:
    """
    Generate JWT token with user information including tenant_id
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'tenant_id': tenant_id,
        'exp': datetime.utcnow() + timedelta(days=30)
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

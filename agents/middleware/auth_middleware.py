import logging
from typing import Optional
import re
import time

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from agents.common.http_utils import add_cors_headers
from agents.utils.jwt_utils import verify_token
from agents.exceptions import ErrorCode
from agents.common.response import RestResponse
from agents.common.error_messages import get_error_message
from agents.services import open_service

security = HTTPBearer()
logger = logging.getLogger(__name__)

class AuthConfig:
    """Authentication configuration"""
    PUBLIC_PATHS = [
        "/api/auth/login", "/api/auth/register",
        "/api/auth/wallet/nonce", "/api/auth/wallet/login",
        "/api/auth/refresh", "/api/auth/reset-password",
        "/api/auth/verify-email", "/docs", "/redoc",
        "/api/health", "/openapi.json", "/api/upload/file",
        "/api/images/generate", "/api/agents/public",
        "/api/categories", "/"
    ]
    PUBLIC_PREFIXES = ["/api/files/", "/api/categories/"]
    OPEN_API_PATHS = [
        r"^/api/agents/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/dialogue$"
    ]

class AuthResponse:
    """Authentication response helper"""
    @staticmethod
    def error(error_code: ErrorCode) -> JSONResponse:
        return add_cors_headers(JSONResponse(
            status_code=200,
            content=RestResponse(
                code=error_code,
                msg=get_error_message(error_code)
            ).model_dump(exclude_none=True)
        ))

class AuthError(Exception):
    def __init__(self, error_code: ErrorCode):
        self.error_code = error_code

class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        
        # Check public paths
        if (path in AuthConfig.PUBLIC_PATHS or
            any(path.startswith(prefix) for prefix in AuthConfig.PUBLIC_PREFIXES)):
            return await call_next(request)

        try:
            # Handle Open API paths
            if any(re.match(pattern, path) for pattern in AuthConfig.OPEN_API_PATHS):
                if await self._authenticate_open_api(request):
                    return await call_next(request)

            # Try JWT authentication
            await self._authenticate_jwt(request)
            return await call_next(request)
        except AuthError as e:
            return AuthResponse.error(e.error_code)
        except Exception as e:
            logger.error("Authentication error", exc_info=True)
            return AuthResponse.error(ErrorCode.TOKEN_INVALID)

    async def _authenticate_open_api(self, request: Request) -> bool:
        """Authenticate using Open API credentials"""
        try:
            headers = request.headers
            access_key = headers.get("X-Access-Key")
            timestamp = headers.get("X-Timestamp")
            signature = headers.get("X-Signature")

            if not all([access_key, timestamp, signature]):
                return False

            if not self._verify_timestamp(timestamp):
                return False

            async with request.app.state.db() as session:
                credentials = await open_service.get_credentials(access_key, session)
                if not credentials or not open_service.verify_signature(
                    access_key, credentials.secret_key, timestamp, signature
                ):
                    return False

                request.state.user = {
                    "id": credentials.user_id,
                    "type": "api_key",
                    "access_key": access_key
                }
                return True
        except Exception:
            logger.error("Open API authentication failed", exc_info=True)
            return False

    async def _authenticate_jwt(self, request: Request):
        """Authenticate using JWT token"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthError(ErrorCode.TOKEN_MISSING)

        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header
        payload = verify_token(token)
        if not payload:
            raise AuthError(ErrorCode.TOKEN_EXPIRED)

        request.state.user = payload

    def _verify_timestamp(self, timestamp: str, max_age: int = 300) -> bool:
        """Verify if timestamp is within allowed range"""
        try:
            current_time = int(time.time())
            request_time = int(timestamp)
            return abs(current_time - request_time) <= max_age
        except ValueError:
            return False

async def get_current_user(request: Request) -> dict:
    """Get authenticated user from request"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail=get_error_message(ErrorCode.UNAUTHORIZED)
        )
    return user

async def get_optional_current_user(request: Request) -> Optional[dict]:
    """Get optional user from request"""
    return getattr(request.state, "user", None)

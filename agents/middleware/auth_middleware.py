import logging
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from agents.common.http_utils import add_cors_headers
from agents.utils.jwt_utils import verify_token
from agents.exceptions import ErrorCode
from agents.common.response import RestResponse
from agents.common.error_messages import get_error_message

security = HTTPBearer()

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        # Whitelist paths that don't require authentication
        auth_whitelist = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/wallet/nonce",  # Wallet nonce endpoint
            "/api/auth/wallet/login",  # Wallet login endpoint
            "/api/auth/refresh",  # Token refresh endpoint
            "/api/auth/reset-password",
            "/api/auth/verify-email",
            "/docs",
            "/redoc",
            "/api/health",
            "/openapi.json",
            "/api/upload/file",
            "/api/images/generate",
            "/api/agents/public",
            "/api/categories",  # Categories list endpoint
            "/"
        ]
        auth_whitelist_startswith = ["/api/files/", "/api/categories/"]

        # Check if the request path is in the whitelist
        for path in auth_whitelist:
            if request.url.path == path:
                return await call_next(request)

        # Check if the request path starts with any of the whitelist prefixes
        for prefix in auth_whitelist_startswith:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return add_cors_headers(JSONResponse(
                    status_code=200,
                    content=RestResponse(
                        code=ErrorCode.TOKEN_MISSING,
                        msg=get_error_message(ErrorCode.TOKEN_MISSING)
                    ).model_dump(exclude_none=True)
                ))

            token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header

            payload = verify_token(token)
            if not payload:
                return add_cors_headers(JSONResponse(
                    status_code=200,
                    content=RestResponse(
                        code=ErrorCode.TOKEN_EXPIRED,
                        msg=get_error_message(ErrorCode.TOKEN_EXPIRED)
                    ).model_dump(exclude_none=True)
                ))

            # Add user information to request state
            request.state.user = payload

        except Exception as e:
            logger.error("Error verifying token", e, exc_info=True)
            return add_cors_headers(JSONResponse(
                status_code=200,
                content=RestResponse(
                    code=ErrorCode.TOKEN_INVALID,
                    msg=get_error_message(ErrorCode.TOKEN_INVALID)
                ).model_dump(exclude_none=True)
            ))

        return await call_next(request)


# FastAPI dependency for getting current user in routes
async def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=get_error_message(ErrorCode.UNAUTHORIZED)
        )
    return user

async def get_optional_current_user(request: Request) -> Optional[dict]:
    """Dependency for optional user authentication"""
    user = getattr(request.state, "user", None)
    return user

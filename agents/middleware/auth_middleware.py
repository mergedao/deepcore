import logging

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from agents.utils.jwt_utils import verify_token

security = HTTPBearer()

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Whitelist paths that don't require authentication
        auth_whitelist = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/wallet/nonce",    # Wallet nonce endpoint
            "/api/auth/wallet/login",    # Wallet login endpoint
            "/api/auth/reset-password",
            "/api/auth/verify-email",
            "/docs",
            "/redoc",
            "/api/health",
            "/openapi.json",
            "/"
        ]
        
        if request.url.path in auth_whitelist:
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing authorization header"}
                )

            token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header
            
            payload = verify_token(token)
            if not payload:
                logger.error("Error verifying token", exc_info=True)
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired token"}
                )

            # Add user information to request state
            request.state.user = payload
        except Exception as e:
            logger.error("Error verifying token", e, exc_info=True)
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"detail": "Could not validate credentials"}
            )

        return await call_next(request)

# FastAPI dependency for getting current user in routes
async def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user 
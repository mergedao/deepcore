from enum import IntEnum


class ErrorCode(IntEnum):
    INTERNAL_ERROR = 10000
    AUTH_ERROR = 10001
    RATELIMITER = 10002
    INVALID_PARAMETERS = 10003

    OPENAPI_ERROR = 10010
    PERMISSION_DENIED = 10011


class CustomAgentException(Exception):
    """Custom exception for agent-related errors."""

    def __init__(self, ErrorCode: ErrorCode = ErrorCode.INTERNAL_ERROR, message: str = "error"):
        self.message = message
        self.ErrorCode = ErrorCode
        super().__init__(self.message)

    def __str__(self):
        return f'{self.ErrorCode.name}: {self.message}'

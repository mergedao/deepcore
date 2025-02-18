from enum import IntEnum
from typing import Optional


class ErrorCode(IntEnum):
    # 系统级错误 (10000-10099)
    INTERNAL_ERROR = 10000
    INVALID_PARAMETERS = 10001
    RATELIMITER = 10002
    
    # 认证相关错误 (10100-10199)
    AUTH_ERROR = 10100
    TOKEN_EXPIRED = 10101
    TOKEN_INVALID = 10102
    TOKEN_MISSING = 10103
    REFRESH_TOKEN_EXPIRED = 10104
    REFRESH_TOKEN_INVALID = 10105
    UNAUTHORIZED = 10106
    
    # 权限相关错误 (10200-10299)
    PERMISSION_DENIED = 10200
    TENANT_INVALID = 10201
    RESOURCE_NOT_FOUND = 10202
    
    # 用户相关错误 (10300-10399)
    USER_NOT_FOUND = 10300
    USER_ALREADY_EXISTS = 10301
    INVALID_CREDENTIALS = 10302
    INVALID_EMAIL = 10303
    
    # 钱包相关错误 (10400-10499)
    WALLET_ERROR = 10400
    WALLET_SIGNATURE_INVALID = 10401
    WALLET_NONCE_EXPIRED = 10402
    
    # API 相关错误 (10500-10599)
    OPENAPI_ERROR = 10500
    API_CALL_ERROR = 10501
    API_RESPONSE_ERROR = 10502


class CustomAgentException(Exception):
    """Custom exception for agent-related errors."""

    def __init__(self, error_code: ErrorCode = ErrorCode.INTERNAL_ERROR, message: Optional[str] = None):
        """
        初始化自定义异常
        
        Args:
            error_code: 错误码
            message: 自定义错误消息，如果不提供则使用错误码对应的默认消息
        """
        from agents.common.error_messages import get_error_message
        self.error_code = error_code
        self.message = message or get_error_message(error_code)
        super().__init__(self.message)

    def __str__(self):
        return f'{self.error_code.name}({self.error_code}): {self.message}'

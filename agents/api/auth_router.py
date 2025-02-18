import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agents.models.db import get_db
from agents.protocol.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, NonceResponse, WalletLoginRequest, WalletLoginResponse
from agents.services import auth_service

router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/login", response_model=LoginResponse, summary="User login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_db)):
    """
    User login endpoint
    
    - **username**: Username or email for login
    - **password**: Password for login
    """
    try:
        result = await auth_service.login(request, session)
        return result
    except Exception as e:
        logger.error( f'Error while user login {request}: {e}', exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.post("/register", response_model=RegisterResponse, summary="User registration")
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_db)):
    """
    User registration endpoint
    
    - **username**: Username for registration
    - **email**: Email address
    - **password**: Password for registration
    """
    try:
        result = await auth_service.register(request, session)
        return result
    except Exception as e:
        logger.error( f'Error while user registration {request}: {e}', exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.post("/wallet/nonce", response_model=NonceResponse)
async def get_nonce(
    wallet_address: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Get nonce for wallet signature
    
    - **wallet_address**: Ethereum wallet address
    """
    try:
        result = await auth_service.get_wallet_nonce(wallet_address, session)
        return result
    except Exception as e:
        logger.error( f'Error while getting nonce for wallet {wallet_address}: {e}', exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.post("/wallet/login", response_model=WalletLoginResponse)
async def wallet_login(
    request: WalletLoginRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Login with wallet signature
    
    - **wallet_type**: Type of wallet (metamask/trust)
    - **wallet_address**: Ethereum wallet address
    - **signature**: Signed message
    """
    try:
        result = await auth_service.wallet_login(request, session)
        return result
    except Exception as e:
        logger.error( f'Error while wallet login {request}: {e}', exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) 
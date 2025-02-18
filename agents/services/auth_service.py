import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import re
import json

from agents.exceptions import CustomAgentException
from agents.models.models import User
from agents.protocol.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, NonceResponse, WalletLoginRequest, WalletLoginResponse
from agents.utils.jwt_utils import generate_token
from agents.utils.web3_utils import generate_nonce, get_message_to_sign, verify_signature
from agents.common.redis_utils import redis_utils

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
NONCE_EXPIRY_MINUTES = 1  # Nonce expires after 5 minutes
NONCE_KEY_PREFIX = "wallet_nonce:"  # Redis key prefix for nonce storage

def get_nonce_key(wallet_address: str) -> str:
    """Generate Redis key for storing nonce"""
    return f"{NONCE_KEY_PREFIX}{wallet_address}"

async def login(request: LoginRequest, session: AsyncSession) -> LoginResponse:
    """
    Handle user login with username or email
    """
    result = await session.execute(
        select(User).where(
            (User.username == request.username) | 
            (User.email == request.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise CustomAgentException(message="Invalid username/email or password")
        
    if not user.check_password(request.password):
        raise CustomAgentException(message="Invalid username/email or password")
        
    # Include tenant_id in token payload
    token = generate_token(
        user_id=user.id,
        username=user.username,
        tenant_id=user.tenant_id
    )
    
    return {
        "token": token,
        "user": user.to_dict()
    }

async def register(request: RegisterRequest, session: AsyncSession) -> RegisterResponse:
    """
    Handle user registration
    """
    if not EMAIL_REGEX.match(request.email):
        raise CustomAgentException(message="Invalid email format")

    if len(request.email) > 120:
        raise CustomAgentException(message="Email is too long")
        
    # Check if username already exists
    result = await session.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none():
        raise CustomAgentException(message="Username already exists")
    
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise CustomAgentException(message="Email already exists")
    
    # Generate tenant_id
    tenant_id = str(uuid.uuid4())
    
    # Create new user with tenant_id
    user = User(
        username=request.username,
        email=request.email,
        tenant_id=tenant_id  # Add tenant_id
    )
    user.set_password(request.password)
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return {
        "message": "User registered successfully",
        "user": user.to_dict()
    }

async def get_wallet_nonce(wallet_address: str, session: AsyncSession) -> NonceResponse:
    """
    Get or generate nonce for wallet signature with expiry time using Redis
    """
    # Generate new nonce and message
    nonce = generate_nonce()
    message = get_message_to_sign(wallet_address, nonce)
    
    # Store nonce in Redis with expiry
    nonce_data = {
        "nonce": nonce,
        "created_at": datetime.utcnow().isoformat()
    }
    redis_utils.set_value(
        get_nonce_key(wallet_address),
        json.dumps(nonce_data),
        ex=NONCE_EXPIRY_MINUTES * 60
    )
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.wallet_address == wallet_address)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create temporary user entry with generated username
        temp_username = f"wallet_{wallet_address[-8:]}"
        
        # Check if the generated username exists
        username_result = await session.execute(
            select(User).where(User.username == temp_username)
        )
        if username_result.scalar_one_or_none():
            temp_username = f"wallet_{wallet_address[-8:]}_{uuid.uuid4().hex[:4]}"
            
        # Create new user with tenant_id
        tenant_id = str(uuid.uuid4())
        user = User(
            username=temp_username,
            wallet_address=wallet_address,
            tenant_id=tenant_id
        )
        session.add(user)
        await session.commit()
    
    return {
        "nonce": nonce,
        "message": message,
        "expires_in": NONCE_EXPIRY_MINUTES * 60
    }

async def wallet_login(request: WalletLoginRequest, session: AsyncSession) -> WalletLoginResponse:
    """
    Handle wallet login/registration with Redis-based nonce verification
    """
    # Get stored nonce data from Redis
    nonce_key = get_nonce_key(request.wallet_address)
    stored_nonce_data = redis_utils.get_value(nonce_key)
    
    if not stored_nonce_data:
        raise CustomAgentException(message="Nonce not found or expired. Please request a new one.")
    
    nonce_data = json.loads(stored_nonce_data)
    nonce = nonce_data["nonce"]
    
    # Get user from database
    result = await session.execute(
        select(User).where(User.wallet_address == request.wallet_address)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise CustomAgentException(message="User not found. Please request a nonce first.")
    
    # Verify signature
    message = get_message_to_sign(request.wallet_address, nonce)
    if not verify_signature(message, request.signature, request.wallet_address):
        raise CustomAgentException(message="Invalid signature")
    
    # Delete used nonce from Redis
    redis_utils.delete_key(nonce_key)
    
    # Set is_new_user flag
    is_new_user = not user.create_time
    
    # Update create_time if this is first login
    if is_new_user:
        user.create_time = datetime.utcnow()
        await session.commit()
    
    # Include tenant_id in token payload
    token = generate_token(
        user_id=user.id,
        username=user.wallet_address,
        tenant_id=user.tenant_id
    )
    
    return {
        "token": token,
        "user": user.to_dict(),
        "is_new_user": is_new_user
    } 
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import re

from agents.exceptions import CustomAgentException
from agents.models.models import User
from agents.protocol.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, NonceResponse, WalletLoginRequest, WalletLoginResponse
from agents.utils.jwt_utils import generate_token
from agents.utils.web3_utils import generate_nonce, get_message_to_sign, verify_signature

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

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
    Get or generate nonce for wallet signature
    """
    # Check if user exists
    result = await session.execute(
        select(User).where(User.wallet_address == wallet_address)
    )
    user = result.scalar_one_or_none()
    
    # Generate new nonce
    nonce = generate_nonce()
    message = get_message_to_sign(wallet_address, nonce)
    
    if user:
        # Update existing user's nonce
        user.nonce = nonce
    else:
        # Create temporary user entry with generated username
        # Generate a username based on wallet address (e.g., "wallet_1234")
        temp_username = f"wallet_{wallet_address[-8:]}"  # Use last 8 characters of wallet address
        
        # Check if the generated username exists
        username_result = await session.execute(
            select(User).where(User.username == temp_username)
        )
        if username_result.scalar_one_or_none():
            # If username exists, add a random suffix
            temp_username = f"wallet_{wallet_address[-8:]}_{uuid.uuid4().hex[:4]}"
            
        # Create new user with tenant_id
        tenant_id = str(uuid.uuid4())
        user = User(
            username=temp_username,
            wallet_address=wallet_address,
            nonce=nonce,
            tenant_id=tenant_id
        )
        session.add(user)
    
    await session.commit()
    
    return {
        "nonce": nonce,
        "message": message
    }

async def wallet_login(request: WalletLoginRequest, session: AsyncSession) -> WalletLoginResponse:
    """
    Handle wallet login/registration
    """
    result = await session.execute(
        select(User).where(User.wallet_address == request.wallet_address)
    )
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        # Create new user with tenant_id for first-time wallet login
        tenant_id = str(uuid.uuid4())
        user = User(
            wallet_address=request.wallet_address,
            nonce=generate_nonce(),
            tenant_id=tenant_id
        )
        session.add(user)
        await session.commit()
        is_new_user = True
    
    # Verify signature
    message = get_message_to_sign(request.wallet_address, user.nonce)
    if not verify_signature(message, request.signature, request.wallet_address):
        raise CustomAgentException(message="Invalid signature")
    
    # Generate new nonce for next login
    user.nonce = generate_nonce()
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
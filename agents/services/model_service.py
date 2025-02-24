import logging
from typing import List, Optional
from fastapi import Depends
from sqlalchemy import select, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from agents.common.config import SETTINGS
from agents.models.db import get_db
from agents.models.models import Model
from agents.exceptions import CustomAgentException, ErrorCode
from agents.protocol.schemas import ModelDTO, ModelCreate, ModelUpdate


cipher_suite = Fernet(SETTINGS.ENCRYPTION_KEY.encode())

logger = logging.getLogger(__name__)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key before storing"""
    if not api_key:
        return None
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key for internal use"""
    if not encrypted_key:
        return None
    return cipher_suite.decrypt(encrypted_key.encode()).decode()

def model_to_dto(model: Model) -> ModelDTO:
    """Convert Model ORM object to DTO"""
    return ModelDTO(
        id=model.id,
        name=model.name,
        model_name=model.model_name,
        endpoint=model.endpoint,
        is_official=model.is_official,
        is_public=model.is_public,
        create_time=model.create_time,
        update_time=model.update_time
    )

async def create_model(
        model: ModelCreate,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    """Create a new model"""
    try:
        # Encrypt API key before storing
        encrypted_api_key = encrypt_api_key(model.api_key) if model.api_key else None
        
        new_model = Model(
            name=model.name,
            model_name=model.model_name,
            endpoint=model.endpoint,
            api_key=encrypted_api_key,  # Store encrypted key
            tenant_id=user.get('tenant_id')
        )
        session.add(new_model)
        await session.flush()
        
        # Return DTO without API key
        return model_to_dto(new_model)
    except Exception as e:
        logger.error(f"Error creating model: {str(e)}")
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create model: {str(e)}"
        )

async def update_model(
        model_id: int,
        model: ModelUpdate,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    """Update an existing model"""
    try:
        result = await session.execute(
            select(Model).where(
                Model.id == model_id,
                Model.tenant_id == user.get('tenant_id')
            )
        )
        db_model = result.scalar_one_or_none()
        if not db_model:
            raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Model not found or no permission")

        # Update fields
        update_data = model.model_dump(exclude_unset=True)
        if 'api_key' in update_data:
            # Encrypt new API key if provided
            update_data['api_key'] = encrypt_api_key(update_data['api_key'])
        
        for key, value in update_data.items():
            setattr(db_model, key, value)
        
        await session.flush()
        
        # Return DTO without API key
        return model_to_dto(db_model)
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error updating model: {str(e)}")
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update model: {str(e)}"
        )

async def list_models(
        user: dict,
        include_public: bool = True,
        only_official: bool = False,
        session: AsyncSession = Depends(get_db)
):
    """List models with filters"""
    conditions = []
    
    if only_official:
        conditions.append(Model.is_official == True)
    else:
        if user and user.get('tenant_id'):
            conditions.append(
                or_(
                    Model.tenant_id == user.get('tenant_id'),
                    and_(Model.is_public == True) if include_public else False
                )
            )
        else:
            conditions.append(Model.is_public == True)
    
    result = await session.execute(
        select(Model).where(and_(*conditions))
    )
    models = result.scalars().all()
    return [model_to_dto(model) for model in models]

async def get_model(
        model_id: int,
        user: dict,
        session: AsyncSession = Depends(get_db)
):
    """Get a specific model"""
    result = await session.execute(
        select(Model).where(
            Model.id == model_id,
            or_(
                Model.tenant_id == user.get('tenant_id'),
                Model.is_public == True
            )
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise CustomAgentException(ErrorCode.INVALID_PARAMETERS, "Model not found or no permission")
    return model_to_dto(model)

async def get_model_with_key(
        model_id: int,
        user: dict,
        session: AsyncSession = Depends(get_db)
) -> Optional[tuple[ModelDTO, str]]:
    """
    Internal method to get model with decrypted API key
    Returns tuple of (model_dto, decrypted_api_key)
    """
    try:
        if user:
            stmt = select(Model).where(
                Model.id == model_id,
                or_(
                    Model.tenant_id == user.get('tenant_id'),
                    Model.is_public == True
                )
            )
        else:
            stmt = select(Model).where(
                Model.id == model_id,
                Model.is_public == True
            )
            
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
            
        return (
            model_to_dto(model),
            decrypt_api_key(model.api_key) if model.api_key else None
        )
    except Exception as e:
        logger.error(f"Error getting model with key: {str(e)}")
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get model: {str(e)}"
        )
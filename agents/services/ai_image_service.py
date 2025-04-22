import logging
from typing import Dict, Any, List, Optional

import httpx
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agents.common.config import SETTINGS
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.models.models import AIImageTemplate

logger = logging.getLogger(__name__)

class CreateAIImageTaskDTO(BaseModel):
    """
    Data transfer object for creating AI image task
    Mode 1: Template + Custom Prompt + Image
    Mode 2: Template + X Link
    """
    template_id: str
    mode: int  # 1: Custom mode, 2: X Link mode
    # Mode 1 fields
    prompt: Optional[str] = None
    image_url: Optional[str] = None
    # Mode 2 fields
    x_link: Optional[str] = None

    def get_twitter_username(self) -> Optional[str]:
        """
        Extract Twitter username from x_link
        Example: https://x.com/ViewsOfChris -> ViewsOfChris
        """
        if not self.x_link:
            return None
        # Remove trailing slash if exists
        x_link = self.x_link.rstrip('/')
        # Split by slash and get the last part
        return x_link.split('/')[-1]

    def validate_fields(self):
        """Validate fields based on mode"""
        if self.mode == 1:
            if not self.prompt or not self.image_url:
                raise CustomAgentException(
                    error_code=ErrorCode.INVALID_PARAMETERS,
                    message="Mode 1 requires prompt and image_url"
                )
        elif self.mode == 2:
            if not self.x_link:
                raise CustomAgentException(
                    error_code=ErrorCode.INVALID_PARAMETERS,
                    message="Mode 2 requires x_link"
                )
        else:
            raise CustomAgentException(
                error_code=ErrorCode.INVALID_PARAMETERS,
                message="Invalid mode, must be 1 or 2"
            )

class AIImageTaskQueryDTO(BaseModel):
    """
    Data transfer object for querying AI image tasks
    """
    page: int = 1
    page_size: int = 20

class AITemplateQueryDTO(BaseModel):
    """Query parameters for AI templates"""
    page: int = 1
    page_size: int = 20

class AITemplateListResponse(BaseModel):
    """Response model for template list"""
    name: str
    preview_url: str
    description: Optional[str]

class AIImageService:
    def __init__(self, session: AsyncSession = Depends(get_db)):
        self.db_session = session
        # Configure base URL and API key
        self.api_base = SETTINGS.DATA_API_BASE
        self.api_key = SETTINGS.DATA_API_KEY

    async def create_ai_image_task(self, task_info: CreateAIImageTaskDTO, tenant_id: str) -> Dict[str, Any]:
        """
        Create a new AI image task
        
        :param task_info: Task information including template_id and mode-specific fields
        :param tenant_id: Tenant ID from user information
        :return: API response data
        """
        # Validate fields based on mode
        task_info.validate_fields()
        
        url = f"{self.api_base}/ps/bnb_img/create_img_task"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        # Get template information
        template = await self.get_template(task_info.template_id)
        if not template:
            raise CustomAgentException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Template not found"
            )
        
        # Prepare payload based on mode
        payload = {
            "tenant_id": tenant_id,
            "template_id": task_info.template_id,
            "mode": task_info.mode
        }
        
        if task_info.mode == 1:
            payload.update({
                "prompt": task_info.prompt,
                "image_url": task_info.image_url
            })
        else:  # mode 2
            twitter_username = task_info.get_twitter_username()
            payload.update({
                "twitter_username": twitter_username,
                "x_link": task_info.x_link
            })
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=httpx.Timeout(30.0))
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Request error for create_ai_image_task: {str(e)}", exc_info=True)
                raise CustomAgentException(
                    error_code=ErrorCode.API_CALL_ERROR,
                    message=f"Failed to create AI image task: {str(e)}"
                )

    async def query_ai_image_task_list(self, query_params: AIImageTaskQueryDTO, tenant_id: str) -> Dict[str, Any]:
        """
        Query AI image task list
        
        :param query_params: Query parameters including page and page_size
        :param tenant_id: Tenant ID from user information
        :return: API response data
        """
        url = f"{self.api_base}/ps/bnb_img/query_img_task_list"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        payload = {
            "tenant_id": tenant_id,
            "page": query_params.page,
            "page_size": query_params.page_size
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=httpx.Timeout(30.0))
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Request error for query_ai_image_task_list: {str(e)}", exc_info=True)
                raise CustomAgentException(
                    error_code=ErrorCode.API_CALL_ERROR,
                    message=f"Failed to query AI image task list: {str(e)}"
                )

    async def query_template_list(self, query_params: AITemplateQueryDTO) -> List[Dict]:
        """
        Query active AI image template list
        
        :param query_params: Query parameters including page and page_size
        :return: List of active templates with basic information
        """
        try:
            # Query only active templates (status = 1)
            query = select(AIImageTemplate).where(AIImageTemplate.status == 1)
            
            # Add pagination
            offset = (query_params.page - 1) * query_params.page_size
            query = query.offset(offset).limit(query_params.page_size)
            
            # Execute query
            result = await self.db_session.execute(query)
            templates = result.scalars().all()
            
            # Format response
            return [
                AITemplateListResponse(
                    name=template.name,
                    preview_url=template.preview_url,
                    description=template.description
                ).dict()
                for template in templates
            ]
        except Exception as e:
            logger.error(f"Error querying template list: {e}", exc_info=True)
            raise CustomAgentException(ErrorCode.API_CALL_ERROR, str(e))

    async def get_template(self, template_id: str) -> Optional[Dict]:
        """
        Get single template by ID
        
        :param template_id: Template ID to retrieve
        :return: Template information or None if not found
        """
        try:
            result = await self.db_session.execute(
                select(AIImageTemplate).where(AIImageTemplate.id == template_id, AIImageTemplate.status == 1)
            )
            template = result.scalars().first()
            
            if not template:
                return None
                
            return AITemplateListResponse(
                name=template.name,
                preview_url=template.preview_url,
                description=template.description,
                status=template.status
            ).dict()
        except Exception as e:
            logger.error(f"Error getting template: {e}", exc_info=True)
            raise CustomAgentException(ErrorCode.API_CALL_ERROR, str(e)) 
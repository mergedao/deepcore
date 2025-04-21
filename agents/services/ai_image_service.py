import logging
from typing import Dict, Any

import httpx
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.config import SETTINGS
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db

logger = logging.getLogger(__name__)

class CreateAIImageTaskDTO(BaseModel):
    """
    Data transfer object for creating AI image task
    """
    x_link: str
    template_img_url: str

    def get_twitter_username(self) -> str:
        """
        Extract Twitter username from x_link
        Example: https://x.com/ViewsOfChris -> ViewsOfChris
        """
        # Remove trailing slash if exists
        x_link = self.x_link.rstrip('/')
        # Split by slash and get the last part
        return x_link.split('/')[-1]

class AIImageTaskQueryDTO(BaseModel):
    """
    Data transfer object for querying AI image tasks
    """
    page: int = 1
    page_size: int = 20

class AIImageService:
    def __init__(self, session: AsyncSession = Depends(get_db)):
        self.db_session = session
        # Configure base URL and API key
        self.api_base = SETTINGS.DATA_API_BASE
        self.api_key = SETTINGS.DATA_API_KEY

    async def create_ai_image_task(self, task_info: CreateAIImageTaskDTO, tenant_id: str) -> Dict[str, Any]:
        """
        Create a new AI image task
        
        :param task_info: Task information including x_link and template_img_url
        :param tenant_id: Tenant ID from user information
        :return: API response data
        """
        url = f"{self.api_base}/ps/bnb_img/create_img_task"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        payload = {
            "tenant_id": tenant_id,
            "template_img_url": task_info.template_img_url,
            "twitter_username": task_info.get_twitter_username()
        }
        
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
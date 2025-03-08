import logging
from typing import Dict, Any, Optional

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.config import SETTINGS
from agents.models.db import get_db

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self, session: AsyncSession = Depends(get_db)):
        self.db_session = session
        # Configure base URL and API key
        self.api_base = SETTINGS.DATA_API_BASE  # Get API base URL from configuration
        self.api_key = SETTINGS.DATA_API_KEY  # Get API key from configuration
    
    async def get_xpro_hot(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Get Xpro Hot data
        :param page: Page number
        :param page_size: Items per page
        :return: API response data
        """
        url = f"{self.api_base}/p/data/xpro/hot"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=httpx.Timeout(30.0))
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Request error for xpro_hot: {str(e)}", exc_info=True)
                raise Exception(f"Failed to fetch xpro_hot data: {str(e)}")
    
    async def get_xpro_ca(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Get Xpro Ca data
        :param page: Page number
        :param page_size: Items per page
        :return: API response data
        """
        url = f"{self.api_base}/p/data/xpro/ca"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=httpx.Timeout(30.0))
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Request error for xpro_ca: {str(e)}", exc_info=True)
                raise Exception(f"Failed to fetch xpro_ca data: {str(e)}") 
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.image_service import ImageService
from ..models.db import get_db

router = APIRouter()

class ImageGenerateRequest(BaseModel):
    content: str
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "standard"

@router.post("/api/images/generate")
async def generate_image(
    request: ImageGenerateRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Image Generation API
    Request body format:
    {
        "content": "Image description",
        "size": "1024x1024",  // Optional, default: 1024x1024
        "quality": "standard" // Optional, options: standard/hd, default: standard
    }
    Response format:
    {
        "file_id": "uuid",
        "url": "/api/files/uuid",
        "metadata": {
            "prompt": "original prompt",
            "size": "image size",
            "quality": "image quality"
        }
    }
    """
    try:
        # Validate size parameter
        valid_sizes = ['1024x1024', '1792x1024', '1024x1792']
        if request.size not in valid_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid size parameter. Available options: {', '.join(valid_sizes)}"
            )
            
        # Validate quality parameter
        valid_qualities = ['standard', 'hd']
        if request.quality not in valid_qualities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quality parameter. Available options: {', '.join(valid_qualities)}"
            )
        
        image_service = ImageService(session)
        result = await image_service.generate_image(
            content=request.content,
            size=request.size,
            quality=request.quality
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

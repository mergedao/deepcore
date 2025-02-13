from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from agents.common.response import RestResponse
from agents.models.db import get_db
from agents.services import file_service
from agents.services.file_service import FileInfo

router = APIRouter()

@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...), session: AsyncSession = Depends(get_db)):
    """
    Upload a file and store it using S3 protocol.
    
    - **file**: File to upload
    """
    result = await file_service.upload_file(file, session)
    return RestResponse(data=result)

@router.get("/files/{fid}")
async def get_file(fid: str, session: AsyncSession = Depends(get_db)):
    """
    Get a presigned URL to download a file from S3 by file name.

    - **fid**: File ID
    """
    file_record: FileInfo = await file_service.query_file(fid, session)
    if file_record:
        return StreamingResponse(
            iter([file_record['file_data']]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{quote(file_record['file_name'])}"}
        )
    raise HTTPException(status_code=404, detail="File not found")
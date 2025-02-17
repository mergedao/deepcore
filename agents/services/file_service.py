import uuid
from abc import ABC, abstractmethod
from typing import TypedDict, Union

from fastapi import Depends
# import boto3
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.models.db import get_db
from agents.models.models import FileStorage


async def upload_file(
        file: UploadFile, 
        user: dict,  # Add user parameter
        session: AsyncSession = Depends(get_db)):
    """
    Upload file with user context
    """
    storage = Storage.get_storage(session)
    fid = await storage.upload_file(file, file.filename, user.get('tenant_id'))
    return {"fid": fid, "url": f"/api/files/{fid}"}


async def query_file(file_uuid: str, session: AsyncSession = Depends(get_db)):
    storage = Storage.get_storage(session)
    file_record: FileInfo = await storage.get_file(file_uuid)
    return file_record


class FileInfo(TypedDict):
    file_name: str
    file_data: bytes
    file_id: str
    file_size: int


class Storage(ABC):
    @abstractmethod
    def upload_file(self, file: UploadFile, file_name: str) -> str:
        pass

    @abstractmethod
    def delete_file(self, file_name: str) -> dict:
        pass

    @abstractmethod
    def get_file(self, file_name: str) -> Union[FileInfo, None]:
        pass

    @staticmethod
    def get_storage(session: AsyncSession):
        storage = DatabaseStorage(session)
        return storage


class DatabaseStorage(Storage):
    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def upload_file(
            self, 
            file: UploadFile, 
            file_name: str,
            tenant_id: str = None  # Add tenant_id parameter
        ) -> str:
        """
        Upload file to database with tenant context
        """
        file_uuid = str(uuid.uuid4())
        file_content = file.file.read()
        new_file = FileStorage(
            file_uuid=file_uuid, 
            file_name=file_name, 
            file_content=file_content, 
            size=file.size,
            tenant_id=tenant_id  # Add tenant_id
        )
        self.db_session.add(new_file)
        await self.db_session.commit()
        return file_uuid

    async def delete_file(self, file_location: str) -> dict:
        pass

    async def get_file(self, fid: str) -> Union[FileInfo, None]:
        result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == fid))
        first = result.scalars().first()
        if first:
            return FileInfo(
                file_name=first.file_name,
                file_data=first.file_content,
                file_id=first.file_uuid,
                file_size=first.size,
            )
        return None

import uuid

from sqlalchemy import Column, String, Boolean, DateTime, func, JSON, Text, LargeBinary, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class App(Base):
    __tablename__ = 'app'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment="UUID ID")
    name = Column(String(255), nullable=False, comment="Name of the app")
    mode = Column(String(50), default='ReAct', comment="Mode of the app: function call, ReAct (default)")
    status = Column(String(50), comment="Status of the app: draft, active, inactive")
    model_json = Column(JSON, comment="Additional fields merged into a JSON column")
    tenant_id = Column(String(255), default=None, comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class Tool(Base):
    __tablename__ = 'tools'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment="UUID ID")
    app_id = Column(String(36), nullable=False, comment="ID of the associated app")
    name = Column(String(255), nullable=False, comment="Name of the tool")
    type = Column(String(50), nullable=False, comment="Type of the tool: function or openAPI")
    content = Column(Text, comment="Content of the tool")
    is_deleted = Column(Boolean, default=False, comment="Logical deletion flag")
    tenant_id = Column(String(255), comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment="UUID ID")
    file_name = Column(String(255), nullable=False, comment="Name of the file")
    file_uuid = Column(String(255), nullable=False, comment="file UUID")
    file_content = Column(LargeBinary, nullable=False, comment="Content of the file")
    size = Column(BigInteger, nullable=False, comment="Size of the file")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")

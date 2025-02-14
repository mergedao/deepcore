from sqlalchemy import Column, String, BigInteger, Boolean, Text, DateTime, func, LargeBinary
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class App(Base):
    __tablename__ = 'app'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    name = Column(String(255), nullable=False, comment="Name of the app")
    description = Column(Text, comment="Description of the app")
    mode = Column(String(50), default='ReAct', comment="Mode of the app: function call, ReAct (default)")
    icon = Column(String(255), comment="Icon URL of the app")
    status = Column(String(50), comment="Status of the app: draft, active, inactive")
    tool_prompt = Column(Text, comment="Prompt for the app's tool")
    max_loops = Column(BigInteger, default=5, comment="Max loops per task, default is 5, max is 10")
    is_deleted = Column(Boolean, default=False, comment="Logical deletion flag")
    tenant_id = Column(String(255), default=None, comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class Tool(Base):
    __tablename__ = 'tools'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    app_id = Column(BigInteger, nullable=False, comment="ID of the associated app")
    name = Column(String(255), nullable=False, comment="Name of the tool")
    type = Column(String(50), nullable=False, comment="Type of the tool: function or openAPI")
    content = Column(Text, comment="Content of the tool")
    is_deleted = Column(Boolean, default=False, comment="Logical deletion flag")
    tenant_id = Column(String(255), comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    file_name = Column(String(255), nullable=False, comment="Name of the file")
    file_uuid = Column(String(255), nullable=False, comment="file UUID")
    file_content = Column(LargeBinary, nullable=False, comment="Content of the file")
    size = Column(BigInteger, nullable=False, comment="Size of the file")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")

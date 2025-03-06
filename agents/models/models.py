import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, func, JSON, Text, LargeBinary, BigInteger, Integer, \
    ForeignKey, Numeric
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from agents.models.base import Base


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Name of the category")
    type = Column(String(50), nullable=False, comment="Type of the category: agent or tool")
    description = Column(Text, comment="Description of the category")
    tenant_id = Column(String(255), comment="Tenant ID")
    sort_order = Column(Integer, default=0, comment="Sort order for display")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")


class App(Base):
    __tablename__ = 'app'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment="UUID ID")
    name = Column(String(255), nullable=False, comment="Name of the app")
    description = Column(Text, comment="Description of the app")
    mode = Column(String(50), default='ReAct', comment="Mode of the app: function call, ReAct (default)")
    icon = Column(String(255), comment="Icon URL of the app")
    status = Column(String(50), comment="Status of the app: draft, active, inactive")
    role_settings = Column(Text, comment="Role settings for the agent")
    welcome_message = Column(Text, comment="Welcome message for the agent")
    twitter_link = Column(String(255), comment="Twitter link for the agent")
    telegram_bot_id = Column(String(255), comment="Telegram bot ID for the agent")
    telegram_bot_name = Column(String(255), comment="Telegram bot name")
    telegram_bot_token = Column(String(1000), comment="Encrypted Telegram bot token")
    token = Column(String(255), comment="Token symbol for the agent")
    symbol = Column(String(50), comment="Symbol for the agent token")
    photos = Column(JSON, comment="Photos for the agent")
    tool_prompt = Column(Text, comment="Tool prompt for the agent")
    max_loops = Column(Integer, default=3, comment="Maximum number of loops the agent can perform")
    model_json = Column(JSON, comment="Additional fields merged into a JSON column")
    tenant_id = Column(String(255), default=None, comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    is_public = Column(Boolean, default=False, comment="Whether the agent is public")
    is_official = Column(Boolean, default=False, comment="Whether the agent is official preset")
    is_hot = Column(Boolean, default=False, comment="Whether the agent is hot")
    create_fee = Column(Numeric(20, 9), default=0.000000000, comment="Fee for creating the agent (tips for creator)")
    price = Column(Numeric(20, 9), default=0.000000000, comment="Fee for using the agent")
    tools = relationship('Tool', secondary='agent_tools', backref='agents')
    suggested_questions = Column(JSON, comment="List of suggested questions for the agent")
    model_id = Column(BigInteger, ForeignKey('models.id'), comment="ID of the associated model")
    category_id = Column(BigInteger, ForeignKey('categories.id'), comment="ID of the category")
    model = relationship('Model')
    category = relationship('Category')


class Tool(Base):
    __tablename__ = 'tools'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="UUID")
    name = Column(String(255), nullable=False)
    description = Column(String(800), nullable=True, comment="Description of the tool")
    type = Column(String(50), nullable=False)
    # OpenAPI specific fields
    origin = Column(String(255), comment="API origin")
    path = Column(String(255), comment="API path")
    method = Column(String(20), comment="HTTP method")
    parameters = Column(JSON, comment="API parameters including header, query, path, and body")
    # Common fields
    auth_config = Column(JSON)
    icon = Column(String(255), comment="Icon URL of the tool")
    is_deleted = Column(Boolean, default=False)
    tenant_id = Column(String(36))
    is_public = Column(Boolean, default=False)
    is_official = Column(Boolean, default=False)
    is_stream = Column(Boolean, default=False, comment="Whether the API returns a stream response")
    output_format = Column(JSON, comment="JSON configuration for formatting API output")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category_id = Column(BigInteger, ForeignKey('categories.id'), comment="ID of the category")
    category = relationship('Category')


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    file_name = Column(String(255), nullable=False, comment="Name of the file")
    file_uuid = Column(String(255), nullable=False, comment="file UUID")
    file_content = Column(LargeBinary, nullable=True, comment="Content of the file (null for S3 storage)")
    size = Column(BigInteger, nullable=False, comment="Size of the file")
    storage_type = Column(String(50), default="database", comment="Storage type: database or s3")
    storage_location = Column(String(1000), nullable=True, comment="Storage location for external storage")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(120), unique=True)
    password = Column(String(255))
    wallet_address = Column(String(42), unique=True)
    nonce = Column(String(32))
    tenant_id = Column(String(255))
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    open_platform_keys = relationship("OpenPlatformKey", back_populates="user")

    def set_password(self, password):
        """Set password."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check password."""
        try:
            return check_password_hash(self.password, password)
        except Exception:
            pass
        return False

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'wallet_address': self.wallet_address,
            'email': self.email
        }


class AgentTool(Base):
    __tablename__ = 'agent_tools'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), ForeignKey('app.id', ondelete='CASCADE'), nullable=False)
    tool_id = Column(String(36), ForeignKey('tools.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class Model(Base):
    __tablename__ = 'models'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Name of the model")
    model_name = Column(String(255), nullable=False, comment="Name of the underlying model (e.g. gpt-4, claude-3)")
    endpoint = Column(String(255), nullable=False, comment="API endpoint of the model")
    api_key = Column(String(1000), comment="API key for the model")
    is_official = Column(Boolean, default=False, comment="Whether the model is official preset")
    is_public = Column(Boolean, default=False, comment="Whether the model is public")
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")


class OpenPlatformKey(Base):
    __tablename__ = "open_platform_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    access_key = Column(String(255), unique=True, nullable=False)
    secret_key = Column(String(255), nullable=False)
    token = Column(String(1000), nullable=True)
    token_created_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="open_platform_keys")

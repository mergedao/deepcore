import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, func, JSON, Text, LargeBinary, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


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
    tool_prompt = Column(Text, comment="Tool prompt for the agent")
    max_loops = Column(Integer, default=3, comment="Maximum number of loops the agent can perform")
    model_json = Column(JSON, comment="Additional fields merged into a JSON column")
    tenant_id = Column(String(255), default=None, comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    is_public = Column(Boolean, default=False, comment="Whether the agent is public")
    is_official = Column(Boolean, default=False, comment="Whether the agent is official preset")
    tools = relationship('Tool', secondary='agent_tools', backref='agents')
    suggested_questions = Column(JSON, comment="List of suggested questions for the agent")
    model_id = Column(BigInteger, ForeignKey('models.id'), comment="ID of the associated model")
    model = relationship('Model')


class Tool(Base):
    __tablename__ = 'tools'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="UUID")
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    auth_config = Column(JSON)
    is_deleted = Column(Boolean, default=False)
    tenant_id = Column(String(36))
    is_public = Column(Boolean, default=False)
    is_official = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    file_name = Column(String(255), nullable=False, comment="Name of the file")
    file_uuid = Column(String(255), nullable=False, comment="file UUID")
    file_content = Column(LargeBinary, nullable=False, comment="Content of the file")
    size = Column(BigInteger, nullable=False, comment="Size of the file")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class User(Base):
    """User Model for storing user related details"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=True)  # Make email optional
    password = Column(String(255), nullable=True)
    wallet_address = Column(String(42), unique=True, nullable=True)  # ETH address is 42 chars with '0x'
    nonce = Column(String(32), nullable=True)  # For wallet signature verification
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Registration time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")

    def set_password(self, password):
        """Set password."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check password."""
        return check_password_hash(self.password, password)

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
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
    endpoint = Column(String(255), nullable=False, comment="API endpoint of the model")
    api_key = Column(String(255), comment="API key for the model")
    is_official = Column(Boolean, default=False, comment="Whether the model is official preset")
    is_public = Column(Boolean, default=False, comment="Whether the model is public")
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")

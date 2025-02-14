from urllib.parse import quote

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from agents.common.config import SETTINGS
from agents.models.models import Base

DATABASE_URL = f"mysql+aiomysql://{SETTINGS.MYSQL_USER}:{quote(SETTINGS.MYSQL_PASSWORD)}@{SETTINGS.MYSQL_HOST}:{SETTINGS.MYSQL_PORT}/{SETTINGS.MYSQL_DB}"

engine = create_async_engine(DATABASE_URL, echo=True)

# Create a global SessionLocal class for generating database sessions
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Dependency for providing a database session in each request
async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == '__main__':
    import asyncio

    asyncio.run(init_db(engine))

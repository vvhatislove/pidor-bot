from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config.config import config
from .models import Base

engine = create_async_engine(config.DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
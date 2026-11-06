from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=True) # makes the connection manager.

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) # factory that creates sessions.


async def get_db():
    """FastAPI dependency – gives each request its own DB session."""
    async with async_session() as session:
        yield session

# “The engine manages the connection pool to the database, 
# and class_=AsyncSession tells the sessionmaker to 
# create async sessions that work with await.”
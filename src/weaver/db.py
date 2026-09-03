import logging
import os

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("weaver.db")
client: AsyncIOMotorClient | None = None


async def init_db():
    global client
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/weaver")
    client = AsyncIOMotorClient(mongo_uri)
    # import models here to avoid circular imports
    from src.weaver.game.models import Event, TurnOrder
    from src.weaver.models.game import GameSession, Room
    from src.weaver.models.user import User
    # ensure dnd adapter import safe
    try:
        from src.weaver.game import dnd_adapter  # noqa: F401
    except Exception:
        pass

    await init_beanie(
        database=client.get_default_database(),
        document_models=[User, Room, GameSession, Event, TurnOrder],
    )
    logger.info("Connected to MongoDB and initialized Beanie")


def close_db():
    global client
    if client:
        client.close()
        logger.info("Closed MongoDB connection")

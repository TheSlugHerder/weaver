import logging
import typing
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

logger = logging.getLogger("weaver.db")
client: typing.Optional[AsyncIOMotorClient] = None


async def init_db():
    global client
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/weaver")
    client = AsyncIOMotorClient(mongo_uri)
    # import models here to avoid circular imports
    from src.weaver.models.user import User
    from src.weaver.models.game import Room, GameSession
    from src.weaver.game.models import Event, TurnOrder
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

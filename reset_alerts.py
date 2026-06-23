import asyncio
from nozzle.db.session import async_session_factory
from nozzle.domain.models import Alert
from nozzle.domain.enums import AlertStatus
from sqlalchemy import update

async def reset():
    async with async_session_factory() as db:
        await db.execute(update(Alert).values(status=AlertStatus.NEW, cluster_id=None))
        await db.commit()
        print("All alerts reset")

asyncio.run(reset())

import asyncio
from datetime import datetime
from nozzle.db.session import async_session_factory
from nozzle.domain.models import User
from nozzle.domain.enums import UserTier
from sqlalchemy import select

async def seed():
    async with async_session_factory() as db:
        r = await db.execute(select(User).where(User.id == "00000000-0000-0000-0000-000000000000"))
        u = r.scalar_one_or_none()
        if u:
            print("Default user already exists")
        else:
            db.add(User(
                id="00000000-0000-0000-0000-000000000000",
                email="admin@nozzle.local",
                hashed_password="none",
                tier=UserTier.PRO,
                alert_limit_daily=50000,
                created_at=datetime.utcnow(),
            ))
            await db.commit()
            print("Default user created")

asyncio.run(seed())

import asyncio
import os
import sys

sys.path.append(os.getcwd())
from app.database.session import Database


async def run():
    db = Database()
    try:
        await db.connect()
        print("Connected")
        await db.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(run())

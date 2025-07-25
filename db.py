import aiosqlite
import sqlite3

DB_PATH = "wallets.db"

# ---------- работа с БД ----------
def init_db_sync():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_addresses ("
            "user_id INTEGER, address TEXT, PRIMARY KEY(user_id, address))"
        )
            
async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS user_addresses ("
            "user_id INTEGER, address TEXT, "
            "PRIMARY KEY(user_id, address))"
        )
        await db.commit()


async def add_address(user_id: int, address: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO user_addresses(user_id, address) VALUES(?, ?)",
                (user_id, address),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def remove_address(user_id: int, address: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM user_addresses WHERE user_id = ? AND address = ?",
            (user_id, address),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_addresses(user_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT address FROM user_addresses WHERE user_id = ?", (user_id,)
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]
import os, json, aiosqlite

def get_db_path() -> str:
    d = os.path.join(os.path.expanduser("~"), ".wanderon")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "wanderon.db")

async def init_db():
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            destination TEXT NOT NULL,
            source_city TEXT DEFAULT '',
            dates TEXT NOT NULL,
            members INTEGER NOT NULL,
            budget TEXT NOT NULL,
            currency TEXT DEFAULT 'INR',
            plan_summary TEXT DEFAULT '',
            full_plan TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            user_id TEXT PRIMARY KEY,
            state TEXT DEFAULT 'idle',
            data TEXT DEFAULT '{}',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

async def save_trip(user_id, destination, source_city, dates, members, budget, currency, plan_summary, full_plan):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO trips (user_id,destination,source_city,dates,members,budget,currency,plan_summary,full_plan) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, destination, source_city, dates, members, budget, currency, plan_summary, full_plan)
        )
        await db.commit()

async def get_session(user_id: str) -> dict:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT state, data FROM sessions WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
    if row:
        return {"state": row["state"], "data": json.loads(row["data"])}
    return {"state": "idle", "data": {}}

async def set_session(user_id: str, state: str, data: dict):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO sessions (user_id,state,data,updated_at) VALUES (?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET state=excluded.state,data=excluded.data,updated_at=excluded.updated_at",
            (user_id, state, json.dumps(data))
        )
        await db.commit()

async def clear_session(user_id: str):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        await db.commit()

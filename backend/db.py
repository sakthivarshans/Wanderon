"""
WanderOn Database Access Layer.
Manages local SQLite database operations, including trip plans storage and session management.
"""
import os, json, aiosqlite

def get_db_path() -> str:
    """
    Resolves the directory path for the local SQLite database.
    Creates the directory if it does not exist under the user's home path (~/.wanderon).
    
    Returns:
        str: Absolute path to the SQLite database file.
    """
    d = os.path.join(os.path.expanduser("~"), ".wanderon")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "wanderon.db")

async def init_db():
    """
    Initializes the local SQLite database schema.
    Creates 'trips' and 'sessions' tables if they are not already present.
    """
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
    """
    Saves a completed trip itinerary plan into the database.
    
    Args:
        user_id (str): Hashed or unique Telegram user ID.
        destination (str): Visited location or destination name.
        source_city (str): Starting point of the trip.
        dates (str): Formatted travel dates.
        members (int): Number of travelers.
        budget (str): Financial budget limit.
        currency (str): Budget currency.
        plan_summary (str): Brief preview snippet of the itinerary.
        full_plan (str): Full text description of the generated itinerary.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO trips (user_id,destination,source_city,dates,members,budget,currency,plan_summary,full_plan) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, destination, source_city, dates, members, budget, currency, plan_summary, full_plan)
        )
        await db.commit()

async def get_session(user_id: str) -> dict:
    """
    Retrieves the current active state and session data for a Telegram user.
    
    Args:
        user_id (str): Telegram user ID.
        
    Returns:
        dict: Containing 'state' (str) and 'data' (dict) of the user session.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT state, data FROM sessions WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
    if row:
        return {"state": row["state"], "data": json.loads(row["data"])}
    return {"state": "idle", "data": {}}

async def set_session(user_id: str, state: str, data: dict):
    """
    Updates or inserts a user's Telegram conversational flow state and context data.
    
    Args:
        user_id (str): Telegram user ID.
        state (str): Conversational state identifier.
        data (dict): State context payload.
    """
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

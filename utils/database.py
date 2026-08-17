import os
import time
import logging
import libsql_client

log = logging.getLogger("database")

_client: libsql_client.Client | None = None


def _get_url() -> str:
    url = os.environ.get("TURSO_DATABASE_URL", "")
    if url.startswith("libsql://") and os.environ.get("TURSO_FORCE_HTTPS", "0") == "1":
        url = url.replace("libsql://", "https://", 1)
    return url


async def init_db():
    global _client
    _client = libsql_client.create_client(
        url=_get_url(),
        auth_token=os.environ.get("TURSO_AUTH_TOKEN", ""),
    )

    await _client.batch([
        """
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            ticket_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at INTEGER NOT NULL,
            closed_at INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS duty_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            start_time INTEGER NOT NULL,
            end_time INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS duty_totals (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            total_seconds INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """,
    ])
    log.info("Database initialized (Turso).")


def client() -> libsql_client.Client:
    if _client is None:
        raise RuntimeError("Database δεν έχει αρχικοποιηθεί ακόμα — κάλεσε init_db() πρώτα.")
    return _client

async def create_ticket(channel_id: int, guild_id: int, user_id: int, ticket_type: str):
    await client().execute(
        "INSERT INTO tickets (channel_id, guild_id, user_id, ticket_type, status, created_at) "
        "VALUES (?, ?, ?, ?, 'open', ?)",
        [channel_id, guild_id, user_id, ticket_type, int(time.time())],
    )


async def close_ticket(channel_id: int):
    await client().execute(
        "UPDATE tickets SET status = 'closed', closed_at = ? WHERE channel_id = ?",
        [int(time.time()), channel_id],
    )


async def get_ticket(channel_id: int):
    rs = await client().execute(
        "SELECT channel_id, guild_id, user_id, ticket_type, status FROM tickets WHERE channel_id = ?",
        [channel_id],
    )
    if not rs.rows:
        return None
    row = rs.rows[0]
    return {
        "channel_id": row[0],
        "guild_id": row[1],
        "user_id": row[2],
        "ticket_type": row[3],
        "status": row[4],
    }

async def start_duty(user_id: int, guild_id: int):
    await client().execute(
        "INSERT INTO duty_sessions (user_id, guild_id, start_time) VALUES (?, ?, ?)",
        [user_id, guild_id, int(time.time())],
    )


async def end_duty(user_id: int, guild_id: int) -> int:
    rs = await client().execute(
        "SELECT id, start_time FROM duty_sessions "
        "WHERE user_id = ? AND guild_id = ? AND end_time IS NULL "
        "ORDER BY id DESC LIMIT 1",
        [user_id, guild_id],
    )
    if not rs.rows:
        return 0

    session_id, start_time = rs.rows[0]
    now = int(time.time())
    duration = now - start_time

    await client().execute(
        "UPDATE duty_sessions SET end_time = ? WHERE id = ?",
        [now, session_id],
    )

    await client().execute(
        "INSERT INTO duty_totals (user_id, guild_id, total_seconds) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, guild_id) DO UPDATE SET total_seconds = total_seconds + ?",
        [user_id, guild_id, duration, duration],
    )
    return duration


async def is_on_duty(user_id: int, guild_id: int) -> bool:
    rs = await client().execute(
        "SELECT id FROM duty_sessions WHERE user_id = ? AND guild_id = ? AND end_time IS NULL",
        [user_id, guild_id],
    )
    return len(rs.rows) > 0


async def get_active_duty_users(guild_id: int) -> list[tuple[int, int]]:
    rs = await client().execute(
        "SELECT user_id, start_time FROM duty_sessions WHERE guild_id = ? AND end_time IS NULL",
        [guild_id],
    )
    return [(row[0], row[1]) for row in rs.rows]


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, int]]:
    rs = await client().execute(
        "SELECT user_id, total_seconds FROM duty_totals "
        "WHERE guild_id = ? ORDER BY total_seconds DESC LIMIT ?",
        [guild_id, limit],
    )
    return [(row[0], row[1]) for row in rs.rows]

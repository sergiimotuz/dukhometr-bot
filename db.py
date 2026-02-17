import os
import asyncpg
from datetime import date, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_id BIGINT UNIQUE NOT NULL,
  lang TEXT NOT NULL DEFAULT 'ua',
  tradition TEXT NOT NULL DEFAULT 'neutral_values',
  tz_offset TEXT NOT NULL DEFAULT '+00:00',
  plan TEXT NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  happened_on DATE NOT NULL,
  type TEXT NOT NULL,
  key TEXT NOT NULL,
  polarity SMALLINT NOT NULL,
  weight SMALLINT NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_user_day ON events(user_id, happened_on);
"""

async def pool():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL env var is required")
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

async def init_db(p):
    async with p.acquire() as con:
        await con.execute(CREATE_SQL)

async def ensure_user(p, tg_id: int, default_lang="ua", default_trad="neutral_values"):
    async with p.acquire() as con:
        row = await con.fetchrow("SELECT * FROM users WHERE tg_id=$1", tg_id)
        if row:
            return row
        row = await con.fetchrow(
            "INSERT INTO users(tg_id, lang, tradition) VALUES ($1,$2,$3) RETURNING *",
            tg_id, default_lang, default_trad
        )
        return row

async def set_lang(p, tg_id: int, lang: str):
    async with p.acquire() as con:
        await con.execute("UPDATE users SET lang=$1 WHERE tg_id=$2", lang, tg_id)

async def set_tradition(p, tg_id: int, trad: str):
    async with p.acquire() as con:
        await con.execute("UPDATE users SET tradition=$1 WHERE tg_id=$2", trad, tg_id)

async def set_tz_offset(p, tg_id: int, tz_offset: str):
    async with p.acquire() as con:
        await con.execute("UPDATE users SET tz_offset=$1 WHERE tg_id=$2", tz_offset, tg_id)

async def get_user(p, tg_id: int):
    async with p.acquire() as con:
        return await con.fetchrow("SELECT * FROM users WHERE tg_id=$1", tg_id)

async def add_event(p, tg_id: int, happened_on: date, typ: str, key: str, polarity: int, weight: int, note: str | None = None):
    async with p.acquire() as con:
        user = await con.fetchrow("SELECT id FROM users WHERE tg_id=$1", tg_id)
        if not user:
            raise RuntimeError("User not found")
        await con.execute(
            "INSERT INTO events(user_id, happened_on, type, key, polarity, weight, note) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            user["id"], happened_on, typ, key, polarity, weight, note
        )

def clamp(n, lo, hi):
    return max(lo, min(hi, n))

def index_from(pos: int, neg: int) -> int:
    return clamp(50 + pos - neg, 0, 100)

async def day_summary(p, tg_id: int, d: date):
    async with p.acquire() as con:
        user = await con.fetchrow("SELECT id FROM users WHERE tg_id=$1", tg_id)
        if not user:
            raise RuntimeError("User not found")
        q = await con.fetchrow("""
            SELECT
              COALESCE(SUM(CASE WHEN polarity=1 THEN weight ELSE 0 END),0) AS pos,
              COALESCE(SUM(CASE WHEN polarity=-1 THEN weight ELSE 0 END),0) AS neg
            FROM events
            WHERE user_id=$1 AND happened_on=$2
        """, user["id"], d)
        pos, neg = int(q["pos"]), int(q["neg"])
        return pos, neg, index_from(pos, neg)

async def week_summary(p, tg_id: int, end: date | None = None):
    if end is None:
        end = date.today()
    start = end - timedelta(days=6)

    async with p.acquire() as con:
        user = await con.fetchrow("SELECT id FROM users WHERE tg_id=$1", tg_id)
        if not user:
            raise RuntimeError("User not found")
        uid = user["id"]

        q = await con.fetchrow("""
            SELECT
              COALESCE(SUM(CASE WHEN polarity=1 THEN weight ELSE 0 END),0) AS pos,
              COALESCE(SUM(CASE WHEN polarity=-1 THEN weight ELSE 0 END),0) AS neg
            FROM events
            WHERE user_id=$1 AND happened_on BETWEEN $2 AND $3
        """, uid, start, end)
        pos, neg = int(q["pos"]), int(q["neg"])

        daily_rows = await con.fetch("""
            SELECT
              happened_on,
              COALESCE(SUM(CASE WHEN polarity=1 THEN weight ELSE 0 END),0) AS pos,
              COALESCE(SUM(CASE WHEN polarity=-1 THEN weight ELSE 0 END),0) AS neg
            FROM events
            WHERE user_id=$1 AND happened_on BETWEEN $2 AND $3
            GROUP BY happened_on
        """, uid, start, end)

        per_day = {r["happened_on"]: (int(r["pos"]), int(r["neg"])) for r in daily_rows}
        total_index = 0
        for i in range(7):
            dd = start + timedelta(days=i)
            ppos, pneg = per_day.get(dd, (0, 0))
            total_index += index_from(ppos, pneg)
        avg = round(total_index / 7)

        return start, end, pos, neg, avg

async def month_summary(p, tg_id: int, end: date | None = None, days: int = 30):
    if end is None:
        end = date.today()
    start = end - timedelta(days=days - 1)

    async with p.acquire() as con:
        user = await con.fetchrow("SELECT id FROM users WHERE tg_id=$1", tg_id)
        if not user:
            raise RuntimeError("User not found")
        uid = user["id"]

        q = await con.fetchrow("""
            SELECT
              COALESCE(SUM(CASE WHEN polarity=1 THEN weight ELSE 0 END),0) AS pos,
              COALESCE(SUM(CASE WHEN polarity=-1 THEN weight ELSE 0 END),0) AS neg
            FROM events
            WHERE user_id=$1 AND happened_on BETWEEN $2 AND $3
        """, uid, start, end)
        pos, neg = int(q["pos"]), int(q["neg"])

        daily_rows = await con.fetch("""
            SELECT
              happened_on,
              COALESCE(SUM(CASE WHEN polarity=1 THEN weight ELSE 0 END),0) AS pos,
              COALESCE(SUM(CASE WHEN polarity=-1 THEN weight ELSE 0 END),0) AS neg
            FROM events
            WHERE user_id=$1 AND happened_on BETWEEN $2 AND $3
            GROUP BY happened_on
        """, uid, start, end)

        per_day = {r["happened_on"]: (int(r["pos"]), int(r["neg"])) for r in daily_rows}
        total_index = 0
        for i in range(days):
            dd = start + timedelta(days=i)
            ppos, pneg = per_day.get(dd, (0, 0))
            total_index += index_from(ppos, pneg)
        avg = round(total_index / days)

        return start, end, pos, neg, avg
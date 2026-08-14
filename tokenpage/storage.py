"""SQLite 存储：~/.tokenpage/prices.db。

每日抓取写入快照。只保留最近 2 天数据，用于涨跌对比。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from tokenpage.config import DATA_DIR

DB_PATH = DATA_DIR / "prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    route_type TEXT DEFAULT 'metered',
    family TEXT,
    tier TEXT,
    prompt_usd REAL,
    completion_usd REAL,
    cache_read_usd REAL,
    cache_write_usd REAL,
    tiered INTEGER,
    is_offpeak INTEGER,
    discount_type TEXT,
    quota_json TEXT,
    zdr_json TEXT,
    deal_tag TEXT,
    currency TEXT,
    raw_prompt REAL,
    raw_completion REAL,
    context_length INTEGER,
    supports_tools INTEGER
);
CREATE INDEX IF NOT EXISTS idx_latest ON prices(provider, model_id, fetched_at);
CREATE INDEX IF NOT EXISTS idx_fetched ON prices(fetched_at);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

_COLS = (
    "fetched_at", "provider", "model_id", "route_type", "family", "tier",
    "prompt_usd", "completion_usd", "cache_read_usd", "cache_write_usd",
    "tiered", "is_offpeak", "discount_type", "quota_json", "zdr_json",
    "deal_tag", "currency", "raw_prompt", "raw_completion",
    "context_length", "supports_tools",
)

_READ_KEYS = (
    "fetched_at", "provider", "model_id", "route_type", "family", "tier",
    "prompt_usd", "completion_usd", "cache_read_usd", "cache_write_usd",
    "tiered", "is_offpeak", "discount_type", "quota_json", "zdr_json",
    "deal_tag", "currency", "raw_prompt", "raw_completion",
    "context_length", "supports_tools",
)


def _b2i(v: bool | None) -> int | None:
    if v is None:
        return None
    return 1 if v else 0


def _i2b(v) -> bool | None:
    if v is None:
        return None
    return bool(v)


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def save_quotes(quotes: list) -> None:
    conn = get_conn()
    try:
        for q in quotes:
            conn.execute(
                f"INSERT INTO prices({','.join(_COLS)}) VALUES({','.join('?' * len(_COLS))})",
                (
                    q.fetched_at,
                    q.provider,
                    q.model_id,
                    q.route_type,
                    q.family,
                    q.tier,
                    q.prompt_usd_per_1m,
                    q.completion_usd_per_1m,
                    q.cache_read_usd_per_1m,
                    q.cache_write_usd_per_1m,
                    _b2i(q.tiered),
                    # 谷时=1 / 峰时=0 / 无规则=NULL（保留三态语义）
                    1 if q.is_offpeak is True else (0 if q.is_offpeak is False else None),
                    q.discount_type,
                    json.dumps(q.quota.__dict__, ensure_ascii=False) if q.quota else None,
                    json.dumps(q.zdr.__dict__, ensure_ascii=False) if q.zdr else None,
                    q.deal_tag,
                    q.currency,
                    q.raw_prompt,
                    q.raw_completion,
                    q.context_length,
                    (1 if q.supports_tools else 0) if q.supports_tools is not None else None,
                ),
            )
        conn.commit()
        prune_old(conn)
    finally:
        conn.close()


def prune_old(conn: sqlite3.Connection | None = None, days: int = 2) -> int:
    """删除超过 days 天的旧快照（默认 2 天），返回删除行数。"""
    own = conn is None
    if own:
        conn = get_conn()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = conn.execute("DELETE FROM prices WHERE fetched_at < ?", (cutoff,))
        conn.commit()
        return cur.rowcount
    finally:
        if own:
            conn.close()


def latest_fetched_at() -> str | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT MAX(fetched_at) FROM prices").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_meta(key: str, default: str | None = None) -> str | None:
    """读取 meta 键值表（如上次强制刷新时间）。"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def set_meta(key: str, value: str) -> None:
    """写入 meta 键值表（存在则覆盖）。"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(r) -> dict:
    d = dict(zip(_READ_KEYS, r))
    d["is_offpeak"] = None if d["is_offpeak"] is None else bool(d["is_offpeak"])
    d["tiered"] = None if d["tiered"] is None else bool(d["tiered"])
    d["supports_tools"] = None if d["supports_tools"] is None else bool(d["supports_tools"])
    d["quota"] = json.loads(d.pop("quota_json")) if d.get("quota_json") else None
    d["zdr"] = json.loads(d.pop("zdr_json")) if d.get("zdr_json") else None
    return d


def latest_quotes() -> list[dict]:
    """返回最近一次抓取的报价（每条为 dict）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT {','.join(_READ_KEYS)}
            FROM prices
            WHERE fetched_at = (SELECT MAX(fetched_at) FROM prices)
            """
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def latest_deals() -> list[dict]:
    """返回最近一次抓取的限时折扣（provider=openrouter_deals）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT {','.join(_READ_KEYS)}
            FROM prices
            WHERE provider = 'openrouter_deals'
              AND fetched_at = (SELECT MAX(fetched_at) FROM prices)
            """
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def batch_fetched_ats() -> list[str]:
    """返回所有抓取批次时间戳（倒序）。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT fetched_at FROM prices ORDER BY fetched_at DESC"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def quotes_for_batch(fetched_at: str) -> list[dict]:
    """返回指定批次的所有报价。"""
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT {','.join(_READ_KEYS)} FROM prices WHERE fetched_at = ?",
            (fetched_at,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def price_diffs() -> dict:
    """对比最近两个批次，返回涨跌/新增/下架信息。

    返回：
    {
      "current": fetched_at,
      "previous": fetched_at | None,
      "changes": [
        {
          "provider", "model_id", "route_type", "family", "tier",
          "action": "down"|"up"|"new"|"gone"|"same",
          "prompt_from", "prompt_to", "completion_from", "completion_to",
        }, ...
      ],
      "summaries": {"down": n, "up": n, "new": n, "gone": n}
    }
    """
    ats = batch_fetched_ats()
    if not ats:
        return {"current": None, "previous": None, "changes": [], "summaries": {}}
    current_at = ats[0]
    previous_at = ats[1] if len(ats) > 1 else None
    cur = quotes_for_batch(current_at)
    prev = quotes_for_batch(previous_at) if previous_at else []

    prev_map = {(r["provider"], r["model_id"]): r for r in prev}
    cur_map = {(r["provider"], r["model_id"]): r for r in cur}

    changes = []
    for key, r in cur_map.items():
        p = prev_map.get(key)
        if p is None:
            changes.append(_change_row(r, None, "new"))
        elif (p["prompt_usd"], p["completion_usd"]) != (r["prompt_usd"], r["completion_usd"]):
            action = "down" if _is_cheaper(p, r) else "up"
            changes.append(_change_row(r, p, action))

    for key, p in prev_map.items():
        if key not in cur_map:
            r = {**p, "fetched_at": current_at}
            changes.append(_change_row(r, p, "gone"))

    summaries = {
        "down": sum(1 for c in changes if c["action"] == "down"),
        "up": sum(1 for c in changes if c["action"] == "up"),
        "new": sum(1 for c in changes if c["action"] == "new"),
        "gone": sum(1 for c in changes if c["action"] == "gone"),
    }
    return {"current": current_at, "previous": previous_at, "changes": changes, "summaries": summaries}


def _is_cheaper(prev: dict, cur: dict) -> bool:
    p = (prev.get("prompt_usd"), prev.get("completion_usd"))
    c = (cur.get("prompt_usd"), cur.get("completion_usd"))
    # 任一价格下降即视为降价（另一价格不变或也降）；输入价优先
    if c[0] is not None and p[0] is not None and c[0] < p[0]:
        return True
    if c[1] is not None and p[1] is not None and c[1] < p[1]:
        return True
    return False


def _change_row(cur: dict, prev: dict | None, action: str) -> dict:
    return {
        "provider": cur.get("provider"),
        "model_id": cur.get("model_id"),
        "route_type": cur.get("route_type"),
        "family": cur.get("family"),
        "tier": cur.get("tier"),
        "action": action,
        "prompt_from": prev.get("prompt_usd") if prev else None,
        "prompt_to": cur.get("prompt_usd"),
        "completion_from": prev.get("completion_usd") if prev else None,
        "completion_to": cur.get("completion_usd"),
    }

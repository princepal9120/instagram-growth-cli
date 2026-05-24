from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .core.client import InstagramPostResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    kind      TEXT NOT NULL,
    value     TEXT NOT NULL,
    count     INTEGER NOT NULL DEFAULT 50,
    added_at  INTEGER NOT NULL,
    PRIMARY KEY (kind, value)
);

CREATE TABLE IF NOT EXISTS posts (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    tag_or_user   TEXT NOT NULL,
    author        TEXT,
    desc          TEXT,
    create_time   INTEGER,
    play_count    INTEGER,
    like_count    INTEGER,
    comment_count INTEGER,
    share_count   INTEGER,
    url           TEXT,
    raw_json      TEXT,
    synced_at     INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    desc,
    author,
    tag_or_user,
    content='posts',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, desc, author, tag_or_user)
    VALUES (new.rowid, new.desc, new.author, new.tag_or_user);
END;

CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, desc, author, tag_or_user)
    VALUES ('delete', old.rowid, old.desc, old.author, old.tag_or_user);
END;

CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, desc, author, tag_or_user)
    VALUES ('delete', old.rowid, old.desc, old.author, old.tag_or_user);
    INSERT INTO posts_fts(rowid, desc, author, tag_or_user)
    VALUES (new.rowid, new.desc, new.author, new.tag_or_user);
END;
"""


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def upsert_posts(
    conn: sqlite3.Connection,
    posts: list[InstagramPostResult],
    source: str,
    tag_or_user: str,
) -> int:
    now = int(time.time())
    processed = 0
    for post in posts:
        if not post.id:
            continue
        processed += 1
        conn.execute(
            """
            INSERT INTO posts
                (id, source, tag_or_user, author, desc, create_time,
                 play_count, like_count, comment_count, share_count, url, raw_json, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source        = excluded.source,
                tag_or_user   = excluded.tag_or_user,
                author        = excluded.author,
                desc          = excluded.desc,
                create_time   = excluded.create_time,
                play_count    = excluded.play_count,
                like_count    = excluded.like_count,
                comment_count = excluded.comment_count,
                share_count   = excluded.share_count,
                url           = excluded.url,
                raw_json      = excluded.raw_json,
                synced_at     = excluded.synced_at
            """,
            (
                post.id,
                source,
                tag_or_user,
                post.author,
                post.desc,
                post.create_time,
                post.play_count,
                post.like_count,
                post.comment_count,
                post.share_count,
                post.url,
                json.dumps(post.raw, ensure_ascii=False) if post.raw else None,
                now,
            ),
        )
    conn.commit()
    return processed


def add_to_watchlist(conn: sqlite3.Connection, kind: str, value: str, count: int = 50) -> None:
    conn.execute(
        """
        INSERT INTO watchlist (kind, value, count, added_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(kind, value) DO UPDATE SET count = excluded.count
        """,
        (kind, value.lstrip("#@"), count, int(time.time())),
    )
    conn.commit()


def remove_from_watchlist(conn: sqlite3.Connection, kind: str, value: str) -> bool:
    cur = conn.execute(
        "DELETE FROM watchlist WHERE kind = ? AND value = ?",
        (kind, value.lstrip("#@")),
    )
    conn.commit()
    return cur.rowcount > 0


def list_watchlist(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT kind, value, count, added_at FROM watchlist ORDER BY added_at DESC"
    ).fetchall()
    return [{"kind": r["kind"], "value": r["value"], "count": r["count"], "added_at": r["added_at"]} for r in rows]


def get_recent_posts(
    conn: sqlite3.Connection,
    since_ts: int,
    limit: int = 100,
) -> list[InstagramPostResult]:
    """Return posts synced after since_ts, ordered by like+comment engagement desc."""
    rows = conn.execute(
        """
        SELECT *,
               (COALESCE(like_count, 0) + COALESCE(comment_count, 0)) AS engagement
        FROM posts
        WHERE synced_at >= ?
        ORDER BY engagement DESC
        LIMIT ?
        """,
        (since_ts, limit),
    ).fetchall()
    return [_row_to_result(r) for r in rows]


def search_local(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 50,
    since_ts: int | None = None,
    until_ts: int | None = None,
) -> list[InstagramPostResult]:
    safe_query = '"' + query.replace('"', '""') + '"'
    clauses: list[str] = ["posts_fts MATCH ?"]
    params: list[Any] = [safe_query]
    if since_ts is not None:
        clauses.append("p.create_time >= ?")
        params.append(since_ts)
    if until_ts is not None:
        clauses.append("p.create_time <= ?")
        params.append(until_ts)
    params.append(limit)
    where = " AND ".join(clauses)
    try:
        rows = conn.execute(
            f"""
            SELECT p.*
            FROM posts p
            JOIN posts_fts f ON p.rowid = f.rowid
            WHERE {where}
            ORDER BY rank
            LIMIT ?
            """,
            params,
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [_row_to_result(r) for r in rows]


def get_cached(
    conn: sqlite3.Connection,
    source: str,
    tag_or_user: str,
    limit: int = 50,
    since_ts: int | None = None,
    until_ts: int | None = None,
) -> list[InstagramPostResult]:
    clauses = ["source = ?", "tag_or_user = ?"]
    params: list[Any] = [source, tag_or_user.lstrip("#@")]
    if since_ts is not None:
        clauses.append("create_time >= ?")
        params.append(since_ts)
    if until_ts is not None:
        clauses.append("create_time <= ?")
        params.append(until_ts)
    params.append(limit)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM posts WHERE {where} ORDER BY synced_at DESC LIMIT ?",
        params,
    ).fetchall()
    return [_row_to_result(r) for r in rows]


def archive_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    sources = conn.execute(
        "SELECT source, tag_or_user, COUNT(*) as n, MAX(synced_at) as last FROM posts GROUP BY source, tag_or_user ORDER BY last DESC"
    ).fetchall()
    db_path = conn.execute("PRAGMA database_list").fetchone()[2]
    size_bytes = Path(db_path).stat().st_size if db_path and Path(db_path).exists() else 0
    return {
        "total_posts": total,
        "size_bytes": size_bytes,
        "sources": [{"source": r["source"], "tag_or_user": r["tag_or_user"], "count": r["n"], "last_synced": r["last"]} for r in sources],
    }


def _row_to_result(row: sqlite3.Row) -> InstagramPostResult:
    raw: dict[str, Any] = {}
    if row["raw_json"]:
        try:
            raw = json.loads(row["raw_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return InstagramPostResult(
        id=row["id"],
        desc=row["desc"],
        author=row["author"],
        create_time=row["create_time"],
        play_count=row["play_count"],
        like_count=row["like_count"],
        comment_count=row["comment_count"],
        share_count=row["share_count"],
        url=row["url"],
        raw=raw,
    )

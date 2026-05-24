from pathlib import Path

import pytest

from ig_cli.core.client import InstagramPostResult
from ig_cli.db import archive_stats, get_cached, init_db, search_local, upsert_posts


def _post(id: str, desc: str, author: str = "founder", source: str = "hashtag") -> InstagramPostResult:
    return InstagramPostResult(
        id=id,
        desc=desc,
        author=author,
        create_time=1700000000,
        play_count=5000,
        like_count=400,
        comment_count=30,
        share_count=10,
        url=f"https://www.instagram.com/p/{id}/",
        raw={"platform": "instagram"},
    )


@pytest.fixture
def db(tmp_path: Path):
    conn = init_db(tmp_path / "test.db")
    yield conn
    conn.close()


def test_init_db_creates_schema(tmp_path: Path):
    conn = init_db(tmp_path / "archive.db")
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' OR type='shadow'").fetchall()}
    conn.close()
    assert "posts" in tables


def test_upsert_and_retrieve(db):
    posts = [_post("abc1", "How to automate founder marketing"), _post("abc2", "Stop wasting time on leads")]
    n = upsert_posts(db, posts, source="hashtag", tag_or_user="aitools")
    assert n == 2

    cached = get_cached(db, "hashtag", "aitools", limit=10)
    assert len(cached) == 2
    ids = {p.id for p in cached}
    assert ids == {"abc1", "abc2"}


def test_upsert_deduplication(db):
    post = _post("dup1", "Original caption")
    upsert_posts(db, [post], source="hashtag", tag_or_user="aitools")

    updated = InstagramPostResult(
        id="dup1",
        desc="Updated caption",
        author="founder",
        create_time=1700000000,
        play_count=9999,
        like_count=800,
        comment_count=60,
        share_count=20,
        url="https://www.instagram.com/p/dup1/",
        raw={},
    )
    upsert_posts(db, [updated], source="hashtag", tag_or_user="aitools")

    rows = db.execute("SELECT COUNT(*) FROM posts WHERE id='dup1'").fetchone()[0]
    assert rows == 1

    cached = get_cached(db, "hashtag", "aitools", limit=10)
    assert cached[0].play_count == 9999


def test_fts_search(db):
    posts = [
        _post("s1", "How to automate content marketing for founders"),
        _post("s2", "Stop wasting time on manual lead generation"),
        _post("s3", "Best tools for solopreneur workflows"),
    ]
    upsert_posts(db, posts, source="hashtag", tag_or_user="buildinpublic")

    results = search_local(db, "automate", limit=10)
    assert len(results) >= 1
    assert any("automate" in (r.desc or "").lower() for r in results)


def test_fts_search_no_results(db):
    results = search_local(db, "xyznonexistentterm123", limit=10)
    assert results == []


def test_fts_malformed_query_returns_empty(db):
    posts = [_post("m1", "automation tools for founders")]
    upsert_posts(db, posts, source="hashtag", tag_or_user="aitools")
    # Unbalanced quote would normally raise sqlite3.OperationalError without sanitization
    results = search_local(db, '"unclosed phrase', limit=10)
    assert results == []


def test_archive_stats(db):
    posts = [_post(f"p{i}", f"caption {i}") for i in range(5)]
    upsert_posts(db, posts, source="hashtag", tag_or_user="aitools")

    stats = archive_stats(db)
    assert stats["total_posts"] == 5
    assert len(stats["sources"]) == 1
    assert stats["sources"][0]["source"] == "hashtag"
    assert stats["sources"][0]["count"] == 5

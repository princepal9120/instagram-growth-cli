from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import instaloader
except Exception:  # pragma: no cover
    instaloader = None  # type: ignore[assignment]


class InstagramBlockedError(RuntimeError):
    """Raised when Instagram blocks, rate-limits, or requires auth."""


@dataclass(slots=True)
class InstagramPostResult:
    id: str | None
    desc: str | None
    author: str | None
    create_time: int | None
    play_count: int | None
    like_count: int | None
    comment_count: int | None
    share_count: int | None
    url: str | None
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "desc": self.desc,
            "author": self.author,
            "create_time": self.create_time,
            "play_count": self.play_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "url": self.url,
            "raw": self.raw,
        }


# Alias keeps the existing market engine reusable across Instagram and Instagram.
VideoResult = InstagramPostResult


def normalize_post(post: Any) -> InstagramPostResult:
    shortcode = getattr(post, "shortcode", None)
    owner = getattr(post, "owner_username", None) or _owner_username(post)
    caption = getattr(post, "caption", None)
    date_utc = getattr(post, "date_utc", None)
    if isinstance(date_utc, datetime):
        create_time = int(date_utc.replace(tzinfo=timezone.utc).timestamp())
    else:
        create_time = None
    is_video = bool(getattr(post, "is_video", False))
    video_views = getattr(post, "video_view_count", None) if is_video else None
    likes = getattr(post, "likes", None)
    comments = getattr(post, "comments", None)
    url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else None
    if is_video and shortcode:
        url = f"https://www.instagram.com/reel/{shortcode}/"
    raw = {
        "platform": "instagram",
        "shortcode": shortcode,
        "typename": getattr(post, "typename", None),
        "is_video": is_video,
        "hashtags": list(getattr(post, "caption_hashtags", []) or []),
        "mentions": list(getattr(post, "caption_mentions", []) or []),
    }
    return InstagramPostResult(
        id=shortcode,
        desc=caption,
        author=owner,
        create_time=create_time,
        play_count=_int(video_views) or _int(likes),
        like_count=_int(likes),
        comment_count=_int(comments),
        share_count=None,
        url=url,
        raw=raw,
    )


def _owner_username(post: Any) -> str | None:
    owner_profile = getattr(post, "owner_profile", None)
    return getattr(owner_profile, "username", None) if owner_profile else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class InstagramTrendClient:
    def __init__(self, username: str | None = None, session_file: str | None = None, request_timeout: float = 20.0) -> None:
        if instaloader is None:
            raise RuntimeError("Instaloader is not installed. Run `pip install -e .[dev]` or install ig-cli dependencies.")
        self.username = username
        self.session_file = session_file
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            request_timeout=request_timeout,
        )
        if username:
            try:
                self.loader.load_session_from_file(username, filename=session_file)
            except Exception:
                # Keep anonymous mode available when there is no saved session yet.
                pass

    async def get_hashtag(self, tag: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        self._reject_proxy(proxy)
        tag = tag.lstrip("#").replace(" ", "")
        return await asyncio.to_thread(self._collect, lambda: instaloader.Hashtag.from_name(self.loader.context, tag).get_posts(), count)

    async def get_user(self, username: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        self._reject_proxy(proxy)
        username = username.lstrip("@")
        return await asyncio.to_thread(self._collect, lambda: instaloader.Profile.from_username(self.loader.context, username).get_posts(), count)

    async def get_reels(self, username: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        self._reject_proxy(proxy)
        username = username.lstrip("@")

        def iterator():
            profile = instaloader.Profile.from_username(self.loader.context, username)
            return (post for post in profile.get_posts() if getattr(post, "is_video", False))

        return await asyncio.to_thread(self._collect, iterator, count)

    async def search(self, query: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        # Instaloader does not expose Instagram's full search. For a CLI workflow,
        # use the strongest hashtag candidate from the query as a deterministic fallback.
        tag = query.lstrip("#").split()[0]
        if not tag:
            raise ValueError("search query cannot be empty")
        return await self.get_hashtag(tag, count=count, proxy=proxy)

    async def get_trending(self, region: str | None = None, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        raise InstagramBlockedError("Instagram has no public trending endpoint. Use `ig market <hashtag> --source hashtag` or `ig profile <username>`.")

    def _collect(self, iterator_factory: Callable[[], Any], count: int) -> list[InstagramPostResult]:
        try:
            rows: list[InstagramPostResult] = []
            for post in iterator_factory():
                rows.append(normalize_post(post))
                if len(rows) >= count:
                    break
            return rows
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "Please wait" in message or "login_required" in message or "401" in message or "403" in message:
                raise InstagramBlockedError("Instagram blocked or requires login. Run `ig login`, lower --count, or retry later.") from exc
            raise RuntimeError(f"Instagram request failed: {exc}") from exc

    def _reject_proxy(self, proxy: str | None) -> None:
        if proxy:
            raise ValueError("Proxy URLs are not supported by the Instaloader backend yet.")

from datetime import datetime

from ig_cli.core.client import normalize_post


class FakePost:
    shortcode = "ABC123"
    owner_username = "creator"
    caption = "How to automate founder marketing #aitools"
    date_utc = datetime(2026, 1, 1)
    is_video = True
    video_view_count = 5000
    likes = 400
    comments = 25
    typename = "GraphVideo"
    caption_hashtags = ["aitools"]
    caption_mentions = []


def test_normalize_post_video():
    result = normalize_post(FakePost())

    assert result.id == "ABC123"
    assert result.author == "creator"
    assert result.play_count == 5000
    assert result.like_count == 400
    assert result.comment_count == 25
    assert result.url == "https://www.instagram.com/reel/ABC123/"
    assert result.raw["platform"] == "instagram"

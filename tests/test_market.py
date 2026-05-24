
from ig_cli.core.client import InstagramPostResult
from ig_cli.market import analyze_market


def post(desc: str, views: int = 10000, likes: int = 900, comments: int = 80, shares: int = 20) -> InstagramPostResult:
    return InstagramPostResult(
        id=desc[:8],
        desc=desc,
        author="founder",
        create_time=None,
        play_count=views,
        like_count=likes,
        comment_count=comments,
        share_count=shares,
        url="https://example.com/post",
        raw={},
    )


def test_analyze_market_scores_and_recommends_actions():
    insight = analyze_market(
        [
            post("How to automate content marketing for indie founders #saas #aitools"),
            post("I built an AI tool to fix slow creator workflows #startup"),
            post("Stop wasting time on manual lead generation. Use this workflow #marketing"),
        ],
        query="ai marketing tools",
        source="hashtag",
    )

    assert insight.videos_analyzed == 3
    assert insight.opportunity_score > 50
    assert insight.decision in {"Create content and validate", "Build or campaign now"}
    assert insight.content_angles
    assert insight.product_opportunities
    assert insight.validation_plan
    assert any(keyword == "marketing" for keyword, _ in insight.top_keywords)
    assert len(insight.reel_ideas) == 5
    assert len(insight.carousel_ideas) == 3
    assert insight.lead_magnet
    assert insight.landing_page_angle


def test_analyze_market_handles_empty_results():
    insight = analyze_market([], query="unknown niche", source="hashtag")

    assert insight.opportunity_score == 0
    assert insight.decision == "Ignore for now"
    assert insight.videos_analyzed == 0
    assert len(insight.reel_ideas) == 5
    assert len(insight.carousel_ideas) == 3
    assert insight.lead_magnet
    assert insight.landing_page_angle


def test_freshness_scoring_recent_posts():
    fixed_now = 1_700_000_000.0  # pinned clock — avoids non-determinism

    recent_post = InstagramPostResult(
        id="1",
        desc="How to automate founder marketing #aitools",
        author="founder",
        create_time=int(fixed_now) - 3600,  # 1 hour before pinned now
        play_count=5000,
        like_count=400,
        comment_count=30,
        share_count=10,
        url="https://example.com/post",
        raw={},
    )
    old_post = InstagramPostResult(
        id="2",
        desc="How to automate founder marketing #aitools",
        author="founder",
        create_time=int(fixed_now) - 30 * 86400,  # 30 days before pinned now
        play_count=5000,
        like_count=400,
        comment_count=30,
        share_count=10,
        url="https://example.com/post",
        raw={},
    )

    insight_recent = analyze_market([recent_post] * 3, query="aitools", source="hashtag", _now=fixed_now)
    insight_old = analyze_market([old_post] * 3, query="aitools", source="hashtag", _now=fixed_now)

    assert insight_recent.opportunity_score > insight_old.opportunity_score

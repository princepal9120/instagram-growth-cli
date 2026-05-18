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


def test_analyze_market_handles_empty_results():
    insight = analyze_market([], query="unknown niche", source="hashtag")

    assert insight.opportunity_score == 0
    assert insight.decision == "Ignore for now"
    assert insight.videos_analyzed == 0

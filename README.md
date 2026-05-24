# instagram-growth-cli

Instagram trend and growth intelligence from the terminal.

`ig` helps entrepreneurs, indie hackers, and creators research Instagram hashtags, profiles, and reels, then turn the signals into product and marketing actions — live or from a local archive.

It uses [Instaloader](https://instaloader.github.io/) as the backend. Works with public Instagram data and can use your own session for more reliable hashtag/profile access.

## Philosophy

This is not just an Instagram downloader.

The goal is to answer: **what should I do with this trend?**

For a niche, hashtag, or competitor profile, `ig` shows:

- posts/reels and metadata
- opportunity score (0–100)
- build / create content / watchlist / ignore decision
- content angles, reel ideas, carousel ideas
- lead magnet and landing page copy
- product opportunities and validation plan

And with the local archive, all of this works **offline**.

## Install

```bash
git clone https://github.com/princepal9120/instagram-growth-cli.git
cd instagram-growth-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Auth

Try public mode first:

```bash
ig hashtag aitools --count 20
ig profile instagram --count 10
```

If Instagram requires a session, login with your own account:

```bash
ig login --username YOUR_USERNAME
ig status
ig logout
```

Session data is stored locally in `~/.ig-cli/`.

## Commands

### Live data

```bash
# Hashtag research
ig hashtag aitools --count 30
ig hashtag buildinpublic --format json

# Profile research
ig profile levelsio --count 20

# Reels/video-like posts
ig reels levelsio --count 20

# Search (hashtag fallback — Instagram full search is private)
ig search "ai tools" --count 20

# Export to JSON or CSV
ig export hashtag aitools --out data/aitools.json --count 100
ig export profile levelsio --out data/levelsio.csv --format csv
```

### Market intelligence

`ig market` turns raw posts into a decision and action plan.

```bash
ig market aitools --source hashtag --count 50
ig market levelsio --source profile --count 30
ig market "solo founder" --source search --format json
```

Output includes:

- opportunity score from reach, engagement, pain/buyer intent, freshness, and hook patterns
- decision: **Build now**, **Create content and validate**, **Watchlist**, or **Ignore**
- top keywords, hashtags, and hook formats
- 4 content angles, 5 reel ideas, 3 carousel ideas
- lead magnet idea and landing page headline
- 3 product opportunities and a 4-step validation plan

### Compare

Compare 2–5 hashtags or profiles side by side:

```bash
ig compare hashtag aitools buildinpublic solofounder
ig compare profile levelsio marc_louvion pieter_levels
ig compare reels levelsio marc_louvion
```

Shows opportunity score, decision, median views, engagement rate, and top keywords for each.

### Local archive (offline mode)

Sync Instagram data to a local SQLite database, then research and analyze without hitting the API again.

```bash
# Fetch and store locally
ig sync hashtag aitools --count 100
ig sync profile levelsio --count 50
ig sync reels levelsio --count 30

# Show archive stats
ig archive

# Search cached posts with full-text search
ig search "automation pain" --local

# Date-range filters on local search/market
ig search "solopreneur" --local --since 2024-01-01 --until 2024-06-30
ig market aitools --source hashtag --local --since 2024-01-01

# Full market analysis from cache — no API call
ig market aitools --source hashtag --local
ig market levelsio --source profile --local
```

Archive stored at `~/.ig-cli/archive.db` (SQLite + FTS5, no extra dependencies).

### Watchlist

Track hashtags and profiles for regular syncing — like a subscription list.

```bash
ig watchlist add --kind hashtag --value aitools --count 100
ig watchlist add --kind profile --value levelsio --count 50
ig watchlist list
ig watchlist list --format json
ig watchlist remove --kind hashtag --value aitools
ig watchlist sync          # sync all watched sources at once
```

### Daily digest & trending

```bash
# Today's top posts from archive (last 24 h, ranked by engagement)
ig today
ig today --hours 48 --format json

# Weekly digest (last 7 days, top by engagement)
ig digest
ig digest --days 14

# All-time top posts from archive
ig top
ig top --count 50 --source hashtag
ig top --format json
```

## Rate limits

Use moderate counts. Instagram can rate-limit or require login for hashtag access. This CLI does not bypass any Instagram restrictions. It only uses public/session-visible data through your own local session.

Tip: `ig sync` once, then use `--local` for all subsequent analysis.

## Roadmap

- Creator watchlists
- Weekly market reports
- Cross-platform compare (TikTok, YouTube Shorts)
- Optional paid backend if public/session access becomes unreliable

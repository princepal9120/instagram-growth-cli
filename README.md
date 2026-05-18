# instagram-growth-cli

Instagram trend and growth intelligence from the terminal.

`ig` helps entrepreneurs, indie hackers, and creators research Instagram hashtags, profiles, and reels, then turn the signals into product and marketing actions.

It uses [Instaloader](https://instaloader.github.io/) as the first backend. That means it works with public Instagram data when available and can use your own Instagram session for more reliable hashtag/profile access.

## Philosophy

This is not just an Instagram downloader.

The goal is to answer: **what should I do with this trend?**

For a niche, hashtag, or competitor profile, `ig` can show:

- posts/reels and metadata
- captions, hashtags, authors, likes, comments, and views when available
- opportunity score
- build/content/watchlist/ignore decision
- content angles
- product opportunities
- validation plan

## Install locally

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
```

Logout:

```bash
ig logout
```

Session data is stored locally in `~/.ig-cli/`.

## Commands

```bash
# Hashtag research
ig hashtag aitools --count 30
ig hashtag buildinpublic --format json

# Profile research
ig profile levelsio --count 20

# Reels/video-like posts for a profile
ig reels levelsio --count 20

# Hashtag fallback search. Instagram full search is private.
ig search "ai tools" --count 20

# Export structured data
ig export hashtag aitools --out data/aitools.json --format json --count 100
ig export profile levelsio --out data/levelsio.csv --format csv --count 50
```

## Market intelligence

Use `ig market` when you want a decision, not just raw posts.

```bash
ig market aitools --source hashtag --count 50
ig market levelsio --source profile --count 30
ig market levelsio --source reels --format json
```

It analyzes:

- opportunity score from reach, engagement, pain words, buyer intent, and repeatable hooks
- decision: build now, create content and validate, watchlist, or ignore
- top keywords, hashtags, and hook formats
- content angles for founders and creators
- product opportunities like lead magnets, micro-tools, and paid workflows
- a validation plan focused on saves/comments/profile clicks/waitlist joins

## Examples

```bash
ig market "solo founder" --source search --count 30
ig market "aitools" --source hashtag --count 50
ig market "notiontemplates" --source hashtag --format json > market-report.json
```

## Known limitations

Instagram does not provide a simple public trending or search API.

So the MVP supports:

- hashtags
- profiles
- reels/video-like posts for profiles
- search via deterministic hashtag fallback

Use moderate counts. Instagram can rate-limit or require login. This CLI does not bypass Instagram restrictions. It only uses public/session-visible data through your own local session.

## Roadmap

- Disk cache for repeated research
- Multi-hashtag comparison
- Creator watchlists
- Weekly market reports
- Cross-platform compare with `instagram-growth-cli`
- Optional paid backend support if public/session access becomes unreliable

# Investors Podcast Bytes

> **The world's best value-investing podcast — distilled into a daily 5-minute read.**

This repo is the raw archive behind a daily Substack newsletter that picks one episode of [**The Investor's Podcast Network**](https://www.theinvestorspodcast.com/) (formerly *We Study Billionaires*) at random, strips out the sponsor reads and small talk, and ships you a tight, opinionated summary every morning.

If you've ever opened your podcast app, seen a 90-minute Buffett episode, sighed, and skipped it — this is for you.

---

## 📬 Subscribe on Substack

> One episode. One short read. Every day.
>
> ### **[→ Subscribe at batlab.substack.com](https://batlab.substack.com)**
>
> Free. No spam. Unsubscribe with one click. Start your morning a little smarter.

What you get:

- **Stock deep dives** distilled — Visa, Tesla, Nintendo, Heico, ASML, Linde, Wise PLC, Kinsale Capital and more — covering the business model, bull case, bear case, and where the hosts disagree with the market.
- **Investing book reviews** — *Margin of Safety*, *Thinking Fast & Slow*, *7 Powers*, *Zero to One*, *The Dhandho Investor*, *Common Stocks and Common Sense* — the frameworks that actually move the needle, not the fluff.
- **Investor profiles** — Mohnish Pabrai, Guy Spier, Joel Greenblatt, Lyn Alden, Francois Rochon — what they buy, why, and where they break from consensus.
- **Market views** — quarterly mastermind discussions, top stock picks for the year, current market opportunities, and what risks the smart money is actually watching.
- **Financial history** — the 1999 dot-com bubble, Julian Robertson's Tiger Fund, the Davis Dynasty, Coca-Cola's golden era — patterns that keep repeating with different tickers.

Each post is **800–1,400 words**, links back to the original episode for the full version, and is structured around 3–5 sections chosen to fit the episode — not a rigid template.

**[Subscribe →](https://batlab.substack.com)** before you forget.

---

## What's actually in this repo

Every file under [`Transcripts/`](Transcripts/) is one episode's publicly-available show notes — title, publish date, episode URL, host description, the *In This Episode You'll Learn* bullets, the books and resources mentioned, and the partial transcript that the show makes public.

Full member-gated transcripts are **not** included. Everything here was scraped from the open episode pages on theinvestorspodcast.com.

```
Investors-Podcast-Bytes/
├── README.md              ← you are here
├── Transcripts/
│   ├── INDEX.md           ← auto-generated table of every episode
│   ├── 01_*.txt
│   ├── 02_*.txt
│   └── …
├── scrape_tip.py          ← refresher script (runs weekly)
├── requirements.txt
└── .gitignore
```

**Episode index:** [`Transcripts/INDEX.md`](Transcripts/INDEX.md) — searchable, sortable, dated, with direct links to every source episode.

---

## How it stays fresh

Every Monday at 09:09 a scheduled refresher (`scrape_tip.py`) walks the listing pages on theinvestorspodcast.com, picks up any new episodes since the last run (capped at 15 per refresh), drops the show notes into `Transcripts/` with a continuing episode number, regenerates `Transcripts/INDEX.md`, and pushes the result here.

Want to run it yourself?

```bash
pip install -r requirements.txt
python3 scrape_tip.py            # default: refresh, push, max 15 new episodes
python3 scrape_tip.py --max 30   # cap at 30 new episodes per run
python3 scrape_tip.py --no-push  # refresh files locally, don't commit
python3 scrape_tip.py --dry-run  # show what would happen, write nothing
```

Auth for `git push` is read from one of these (in order): `$GITHUB_TOKEN`, `./.gh_token`, or `~/.critechery_github_token`. If none is set, it scrapes locally and prints commit/push instructions.

---

## How the daily Substack post is made

The Substack post you read every morning isn't generated from this repo by humans — there's a separate daily task (`investor-bytes-daily-summarizer`) that:

1. Picks one random unpublished episode from `Transcripts/`.
2. Classifies it into one of six archetypes (stock deep dive, book review, market view, investor profile, history, or framework) and chooses 3–5 sections from a per-archetype menu so the post actually fits the episode.
3. Strips the SUBSCRIBE / sponsors / "help us out" boilerplate.
4. Writes the post — conversational, opinionated, with verbatim quotes where they land — and ships it to [batlab.substack.com](https://batlab.substack.com).

One post a day. Every day. No re-runs of the same episode.

**[See it in your inbox →](https://batlab.substack.com)**

---

## Disclaimers

- **Not investment advice.** Nothing in this repo, on Substack, or in the source episodes constitutes financial, investment, tax, or legal advice. Do your own work before buying or selling anything.
- **Source content** © The Investor's Podcast Network. Episode summaries, the *In This Episode You'll Learn* bullets, and any partial transcripts here are scraped from publicly-accessible show-notes pages and reproduced under fair-use for archival and educational purposes. Full member-only transcripts are not included.
- **Newsletter content** is original commentary on the public summaries — not a verbatim re-publish of the podcast.

---

*If this archive is useful to you, the easiest way to say thanks is to* [**hit subscribe on Substack**](https://batlab.substack.com) *— that's what keeps the daily summarizer running.*

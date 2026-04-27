#!/usr/bin/env python3
"""
scrape_tip.py — Investors Podcast Bytes refresher.

What it does
------------
1. Scans this directory for already-saved episode .txt files (looks at the
   `URL:` line in each file, not the filename — so reordering / renumbering is fine).
2. Walks listing pages on theinvestorspodcast.com (newest first) until it has
   collected up to MAX_NEW *new* episode URLs.
3. Fetches each new episode page, extracts the public show-notes summary,
   and writes a numbered .txt file (continuing the existing numbering).
4. Regenerates README.md as an index of every episode.
5. Optionally: commits and pushes to the GitHub repo.

Auth for git push
-----------------
Looks for a GitHub token in this order:
  1. $GITHUB_TOKEN environment variable
  2. ./.gh_token (in the repo dir; gitignored)
  3. ~/.critechery_github_token (the same token used by git_critechery)

If no token is found, the script still scrapes + writes files but skips the
push (it'll print instructions for finishing manually).

Usage
-----
    python3 scrape_tip.py                # default: refresh, push, MAX_NEW=15
    python3 scrape_tip.py --max 30       # cap at 30 new episodes per run
    python3 scrape_tip.py --no-push      # just refresh files locally
    python3 scrape_tip.py --dry-run      # show what would happen, write nothing

Dependencies: beautifulsoup4 (`pip3 install beautifulsoup4`)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

LISTING = "https://www.theinvestorspodcast.com/the-investors-podcast-show/"
LISTING_PAGE_FMT = "https://www.theinvestorspodcast.com/the-investors-podcast-show/page/{n}/"
EPISODE_RX = re.compile(r"https://www\.theinvestorspodcast\.com/episodes/[^\"']+")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

REPO_DIR = Path(__file__).resolve().parent
REMOTE_REPO = "batlabx/Investors-Podcast-Bytes"


# -------- HTTP --------

def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def gather_listing_urls(max_pages: int = 25) -> list[str]:
    """Walk listing pages newest-first, return ordered list of episode URLs."""
    seen, ordered = set(), []
    pages_to_try = [LISTING] + [LISTING_PAGE_FMT.format(n=n) for n in range(2, max_pages + 1)]
    consecutive_no_new = 0
    for u in pages_to_try:
        try:
            html = fetch(u)
        except Exception as e:
            print(f"  ! listing fetch failed for {u}: {e}", file=sys.stderr)
            continue
        before = len(ordered)
        for m in EPISODE_RX.finditer(html):
            url = m.group(0)
            if url not in seen:
                seen.add(url); ordered.append(url)
        added = len(ordered) - before
        if added == 0:
            consecutive_no_new += 1
            if consecutive_no_new >= 3:
                break  # listing exhausted / heavy overlap
        else:
            consecutive_no_new = 0
    return ordered


# -------- extraction --------

BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
              "tr", "br", "section", "article", "ul", "ol", "blockquote"}
SKIP_TAGS = {"script", "style", "svg", "noscript", "iframe"}
GATE_RX = re.compile(
    r"READ MORE\s*The full transcript is only available to logged-in users.*?account here\.?",
    re.S | re.I,
)
DATE_RX = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b"
)


def block_text(node) -> str:
    out: list[str] = []

    def walk(el):
        if el.name == "br":
            out.append("\n"); return
        if isinstance(el, str):
            out.append(el); return
        if el.name in SKIP_TAGS:
            return
        for c in el.children:
            if hasattr(c, "name"): walk(c)
            else: out.append(str(c))
        if el.name in BLOCK_TAGS:
            out.append("\n")

    walk(node)
    text = "".join(out)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_episode(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.find("meta", property="og:title") or {}).get("content", "").strip()
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
    date = ""
    t = soup.find("time")
    if t:
        date = t.get("datetime", "") or t.get_text(strip=True)
    if not date:
        pc = soup.select_one("div.post-content")
        if pc:
            m = DATE_RX.search(pc.get_text(" ", strip=True))
            if m: date = m.group(0)
    summary_node = soup.select_one("div.podcast-post-content") or soup.select_one("div.post-content")
    summary = block_text(summary_node) if summary_node else ""
    summary = GATE_RX.sub("", summary).strip()
    return {"title": title, "url": url, "date": date, "body": summary}


# -------- file management --------

def slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1][:80]


def existing_episodes(repo_dir: Path) -> tuple[set[str], int]:
    """Return (set of URLs already saved, highest episode number used)."""
    seen = set()
    high = 0
    for p in glob.glob(str(repo_dir / "[0-9]*_*.txt")):
        name = os.path.basename(p)
        m = re.match(r"^(\d+)_", name)
        if m:
            high = max(high, int(m.group(1)))
        try:
            with open(p, encoding="utf-8") as f:
                head = "".join([next(f, "") for _ in range(10)])
            for url_match in re.finditer(r"^URL:\s+(\S+)", head, re.M):
                seen.add(url_match.group(1).rstrip("/") + "/")
        except Exception:
            pass
    return seen, high


def write_txt(d: dict, idx: int, repo_dir: Path) -> Path:
    fname = f"{idx:02d}_{slug(d['url'])}.txt" if idx < 100 else f"{idx:03d}_{slug(d['url'])}.txt"
    path = repo_dir / fname
    parts = [
        d["title"],
        "=" * max(40, len(d["title"])),
        f"URL:  {d['url']}",
        f"Date: {d['date']}",
        "",
        d["body"],
    ]
    path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return path


def regenerate_readme(repo_dir: Path) -> Path:
    files = sorted(glob.glob(str(repo_dir / "[0-9]*_*.txt")),
                   key=lambda p: int(re.match(r"^(\d+)_", os.path.basename(p)).group(1)))
    rows = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            head = [next(f, "") for _ in range(4)]
        title = head[0].strip()
        url = ""
        date = ""
        for ln in head:
            m = re.match(r"URL:\s+(\S+)", ln)
            if m: url = m.group(1)
            m = re.match(r"Date:\s+(.+)", ln)
            if m: date = m.group(1).strip()
        fname = os.path.basename(fp)
        m = re.match(r"^(\d+)_", fname)
        rows.append((m.group(1), title, date, url, fname))

    out = [
        "# Investors Podcast Bytes",
        "",
        "Episode summaries from **The Investor's Podcast** (formerly *We Study Billionaires*), "
        "scraped from the show notes on theinvestorspodcast.com.",
        "",
        "Each `.txt` file contains the title, publish date, source URL, episode summary, "
        "the *In this episode you'll learn* bullets, books and resources referenced, and sponsor list "
        "— i.e. everything publicly available on the episode page (full transcripts are member-gated and not included).",
        "",
        f"**{len(rows)} episodes** archived. Most recent first.",
        "",
        "| # | Title | Date | Source |",
        "|---|-------|------|--------|",
    ]
    for num, title, date, url, fname in rows:
        safe_title = title.replace("|", "\\|")
        out.append(f"| {num} | [{safe_title}]({fname}) | {date} | [theinvestorspodcast.com]({url}) |")
    out += ["", "---", "", "*Generated by `scrape_tip.py`. Source content © The Investor's Podcast Network.*", ""]
    path = repo_dir / "README.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return path


# -------- git --------

def find_token() -> str | None:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()
    for p in [REPO_DIR / ".gh_token", Path.home() / ".critechery_github_token"]:
        if p.exists():
            t = p.read_text(encoding="utf-8").strip()
            if t: return t
    return None


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, capture: bool = False):
    kw = {"cwd": str(cwd) if cwd else None}
    if capture:
        kw["stdout"] = subprocess.PIPE; kw["stderr"] = subprocess.PIPE
    res = subprocess.run(cmd, **kw)
    if check and res.returncode != 0:
        if capture:
            print(res.stdout.decode(errors="ignore"), file=sys.stderr)
            print(res.stderr.decode(errors="ignore"), file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return res


def git_commit_and_push(repo_dir: Path, n_new: int, token: str | None) -> None:
    if not shutil.which("git"):
        print("! git not installed; skipping push", file=sys.stderr)
        return

    # Initialise repo metadata if missing
    if not (repo_dir / ".git").exists():
        run(["git", "init"], cwd=repo_dir)
        run(["git", "checkout", "-b", "main"], cwd=repo_dir, check=False)
    run(["git", "config", "user.email", "batlab.x@gmail.com"], cwd=repo_dir, check=False)
    run(["git", "config", "user.name", "Abhishek Bathla"], cwd=repo_dir, check=False)

    # Check for changes
    res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_dir),
                         stdout=subprocess.PIPE)
    if not res.stdout.strip():
        print("Nothing to commit; working tree clean.")
        return

    run(["git", "add", "-A"], cwd=repo_dir)
    msg = f"Refresh: +{n_new} new episode summaries" if n_new else "Refresh README"
    run(["git", "commit", "-m", msg], cwd=repo_dir)

    if not token:
        print("! no GitHub token found — committed locally but not pushed.", file=sys.stderr)
        print("  set GITHUB_TOKEN, drop a token at ./.gh_token, or use ~/.critechery_github_token", file=sys.stderr)
        return

    remote_url = f"https://x-access-token:{token}@github.com/{REMOTE_REPO}.git"
    # Ensure remote is set
    res = subprocess.run(["git", "remote"], cwd=str(repo_dir), stdout=subprocess.PIPE)
    remotes = res.stdout.decode().split()
    if "origin" not in remotes:
        run(["git", "remote", "add", "origin", remote_url], cwd=repo_dir)
    else:
        run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_dir, check=False)
    run(["git", "push", "-u", "origin", "main"], cwd=repo_dir)
    print("Pushed to https://github.com/" + REMOTE_REPO)


# -------- main --------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=15, help="max new episodes per run (default 15)")
    ap.add_argument("--no-push", action="store_true", help="don't commit/push to GitHub")
    ap.add_argument("--dry-run", action="store_true", help="discover new episodes, but don't write or push")
    args = ap.parse_args()

    print(f"Scanning {REPO_DIR}…")
    saved_urls, high = existing_episodes(REPO_DIR)
    print(f"  {len(saved_urls)} episodes already saved (highest # = {high})")

    print("Walking listing pages…")
    listing = gather_listing_urls(max_pages=25)
    print(f"  {len(listing)} listing URLs collected")

    new_urls = [u for u in listing
                if (u.rstrip('/') + '/') not in saved_urls
                and u not in saved_urls][: args.max]
    if not new_urls:
        print("No new episodes — nothing to do.")
        if not args.dry_run and not args.no_push:
            # Still regenerate README if needed
            regenerate_readme(REPO_DIR)
            git_commit_and_push(REPO_DIR, 0, find_token())
        return 0

    print(f"Found {len(new_urls)} new episodes to fetch (cap={args.max}):")
    for u in new_urls:
        print("  -", u)

    if args.dry_run:
        return 0

    next_idx = high + 1
    written = 0
    for url in new_urls:
        try:
            html = fetch(url)
            d = extract_episode(html, url)
            p = write_txt(d, next_idx, REPO_DIR)
            print(f"  [{next_idx:03d}] {p.name}  ({len(d['body'])} chars)")
            next_idx += 1
            written += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  ! failed {url}: {e}", file=sys.stderr)

    print(f"Wrote {written} new files. Regenerating README.md…")
    regenerate_readme(REPO_DIR)

    if args.no_push:
        print("--no-push set; skipping commit/push.")
        return 0

    token = find_token()
    git_commit_and_push(REPO_DIR, written, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

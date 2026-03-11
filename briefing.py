#!/usr/bin/env python3
"""
Economics Journal Weekly Briefing
──────────────────────────────────────────────────────────────────────────────
Automatically emails you new papers from top economics journals every week
(or month). Papers are sourced from public RSS feeds. No duplicates ever sent.

HOW TO CUSTOMISE:
  1. To remove a journal  →  add a # at the start of its 4 lines below
  2. To add a journal     →  copy any block and update name/rss/home/abs
  3. To change schedule   →  edit the cron line in .github/workflows/briefing.yml
  4. To change lookback   →  edit DAYS_LOOKBACK below (set to 32 for monthly)
"""

import json
import logging
import os
import sys
import time
import resend
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import feedparser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# ── Credentials (set these as GitHub Secrets — never hardcode here) ───────────
RESEND_API_KEY  = os.environ["RESEND_API_KEY"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
SENDER_EMAIL    = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

# ── How far back to look for new papers ───────────────────────────────────────
# 8  = weekly digest (looks back 8 days to allow for weekend delays)
# 32 = monthly digest (looks back 32 days)
DAYS_LOOKBACK = int(os.getenv("DAYS_LOOKBACK", "8"))

TRACKING_FILE = Path(__file__).with_name("sent_papers.json")
REQUEST_DELAY = 1.5    # polite pause between RSS requests (seconds)
PRUNE_DAYS    = 180    # auto-remove tracking entries older than this


# ══════════════════════════════════════════════════════════════════════════════
#  JOURNAL LIST — comment out any journal you don't want
#
#  Each entry has 4 lines:
#    "Journal Name": {
#        "rss":  "<RSS feed URL>",
#        "home": "<Journal homepage URL>",
#        "abs":  "<ABS rating, e.g. 4* or 4>",   ← label only, cosmetic
#    },
#
#  To REMOVE a journal: add  #  at the start of all 4 lines
#  To ADD a journal:    copy any block, paste it, and update the 4 values
# ══════════════════════════════════════════════════════════════════════════════
JOURNALS: Dict[str, Dict] = {

    # ── ABS 4* ────────────────────────────────────────────────────────────────

    "American Economic Review": {
        "rss":  "https://www.aeaweb.org/journals/aer/feed",
        "home": "https://www.aeaweb.org/journals/aer",
        "abs":  "4*",
    },
    "Econometrica": {
        "rss":  "https://onlinelibrary.wiley.com/feed/14680262/most-recent",
        "home": "https://www.econometricsociety.org/publications/econometrica",
        "abs":  "4*",
    },
    "Journal of Political Economy": {
        "rss":  "https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jpe",
        "home": "https://www.journals.uchicago.edu/journal/jpe",
        "abs":  "4*",
    },
    "Quarterly Journal of Economics": {
        "rss":  "https://academic.oup.com/rss/site_5504/3365.xml",
        "home": "https://academic.oup.com/qje",
        "abs":  "4*",
    },
    "Review of Economic Studies": {
        "rss":  "https://academic.oup.com/rss/site_5508/3369.xml",
        "home": "https://academic.oup.com/restud",
        "abs":  "4*",
    },
    "Management Science": {
        "rss":  "https://pubsonline.informs.org/action/showFeed?type=etoc&feed=rss&jc=mnsc",
        "home": "https://pubsonline.informs.org/journal/mnsc",
        "abs":  "4*",
    },
    "Journal of Finance": {
        "rss":  "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
        "home": "https://onlinelibrary.wiley.com/journal/15406261",
        "abs":  "4*",
    },
    "Review of Financial Studies": {
        "rss":  "https://academic.oup.com/rss/site_5512/3373.xml",
        "home": "https://academic.oup.com/rfs",
        "abs":  "4*",
    },
    "Journal of Financial Economics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/0304405X",
        "home": "https://www.sciencedirect.com/journal/journal-of-financial-economics",
        "abs":  "4*",
    },

    # ── ABS 4 ─────────────────────────────────────────────────────────────────

    "AEJ: Applied Economics": {
        "rss":  "https://www.aeaweb.org/journals/app/feed",
        "home": "https://www.aeaweb.org/journals/app",
        "abs":  "4",
    },
    "AEJ: Economic Policy": {
        "rss":  "https://www.aeaweb.org/journals/pol/feed",
        "home": "https://www.aeaweb.org/journals/pol",
        "abs":  "4",
    },
    "AEJ: Macroeconomics": {
        "rss":  "https://www.aeaweb.org/journals/mac/feed",
        "home": "https://www.aeaweb.org/journals/mac",
        "abs":  "4",
    },
    "AEJ: Microeconomics": {
        "rss":  "https://www.aeaweb.org/journals/mic/feed",
        "home": "https://www.aeaweb.org/journals/mic",
        "abs":  "4",
    },
    "Economic Journal": {
        "rss":  "https://academic.oup.com/rss/site_5502/3363.xml",
        "home": "https://academic.oup.com/ej",
        "abs":  "4",
    },
    "International Economic Review": {
        "rss":  "https://onlinelibrary.wiley.com/feed/14682354/most-recent",
        "home": "https://onlinelibrary.wiley.com/journal/14682354",
        "abs":  "4",
    },
    "Journal of Applied Econometrics": {
        "rss":  "https://onlinelibrary.wiley.com/feed/10991255/most-recent",
        "home": "https://onlinelibrary.wiley.com/journal/10991255",
        "abs":  "4",
    },
    "Journal of Development Economics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/03043878",
        "home": "https://www.sciencedirect.com/journal/journal-of-development-economics",
        "abs":  "4",
    },
    "Journal of Econometrics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/03044076",
        "home": "https://www.sciencedirect.com/journal/journal-of-econometrics",
        "abs":  "4",
    },
    "Journal of Economic Literature": {
        "rss":  "https://www.aeaweb.org/journals/jel/feed",
        "home": "https://www.aeaweb.org/journals/jel",
        "abs":  "4",
    },
    "Journal of Economic Perspectives": {
        "rss":  "https://www.aeaweb.org/journals/jep/feed",
        "home": "https://www.aeaweb.org/journals/jep",
        "abs":  "4",
    },
    "Journal of Economic Theory": {
        "rss":  "https://rss.sciencedirect.com/publication/science/00220531",
        "home": "https://www.sciencedirect.com/journal/journal-of-economic-theory",
        "abs":  "4",
    },
    "Journal of Human Resources": {
        "rss":  "https://jhr.uwpress.org/rss/current.xml",
        "home": "https://jhr.uwpress.org",
        "abs":  "4",
    },
    "Journal of International Economics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/00221996",
        "home": "https://www.sciencedirect.com/journal/journal-of-international-economics",
        "abs":  "4",
    },
    "Journal of Labor Economics": {
        "rss":  "https://www.journals.uchicago.edu/action/showFeed?type=etoc&feed=rss&jc=jole",
        "home": "https://www.journals.uchicago.edu/journal/jole",
        "abs":  "4",
    },
    "Journal of Monetary Economics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/03043932",
        "home": "https://www.sciencedirect.com/journal/journal-of-monetary-economics",
        "abs":  "4",
    },
    "Journal of Public Economics": {
        "rss":  "https://rss.sciencedirect.com/publication/science/00472727",
        "home": "https://www.sciencedirect.com/journal/journal-of-public-economics",
        "abs":  "4",
    },
    "RAND Journal of Economics": {
        "rss":  "https://onlinelibrary.wiley.com/feed/17562171/most-recent",
        "home": "https://onlinelibrary.wiley.com/journal/17562171",
        "abs":  "4",
    },
    "Review of Economics and Statistics": {
        "rss":  "https://direct.mit.edu/rest/issue-rss-feed",
        "home": "https://direct.mit.edu/rest",
        "abs":  "4",
    },

}


# ══════════════════════════════════════════════════════════════════════════════
#  Everything below this line is the engine — no need to edit
# ══════════════════════════════════════════════════════════════════════════════

def load_tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except json.JSONDecodeError:
            log.warning("Tracking file corrupt — starting fresh.")
    return {}


def save_tracking(data: dict) -> None:
    TRACKING_FILE.write_text(json.dumps(data, indent=2))
    log.info("Tracking file saved (%d entries).", len(data))


def prune_tracking(data: dict) -> dict:
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=PRUNE_DAYS)
    ).isoformat()
    return {k: v for k, v in data.items() if v >= cutoff}


def entry_dt(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def entry_authors(entry) -> str:
    if hasattr(entry, "authors"):
        names = [a.get("name", "").strip() for a in entry.authors if a.get("name")]
        if names:
            return ", ".join(names)
    if hasattr(entry, "author") and entry.author:
        return entry.author.strip()
    return ""


def fetch_journal(
    name: str, info: dict, cutoff: datetime, sent: set
) -> List[dict]:
    papers: List[dict] = []
    try:
        feed = feedparser.parse(info["rss"])
        if feed.bozo and not feed.entries:
            log.warning("  %-42s  feed error: %s", name, feed.bozo_exception)
            return papers
        log.info("  %-42s  %d entries", name, len(feed.entries))
        for entry in feed.entries:
            url = getattr(entry, "link", None) or getattr(entry, "id", None)
            if not url:
                continue
            if url in sent:
                continue
            pub = entry_dt(entry)
            if pub and pub < cutoff:
                continue
            papers.append({
                "id":       url,
                "title":    getattr(entry, "title", "(no title)").strip(),
                "authors":  entry_authors(entry),
                "url":      url,
                "pub_date": pub.strftime("%-d %b %Y") if pub else "",
            })
    except Exception as exc:
        log.warning("  %-42s  error: %s", name, exc)
    return papers


_BADGE = (
    "display:inline-block;background:{bg};color:#fff;"
    "font-size:11px;font-weight:bold;padding:2px 8px;"
    "border-radius:10px;margin-left:8px;vertical-align:middle;"
)

def abs_badge(rating: str) -> str:
    bg = "#0a3161" if rating == "4*" else "#2c6fad"
    return f'<span style="{_BADGE.format(bg=bg)}">ABS {rating}</span>'


def build_html(results: Dict[str, List[dict]], date_label: str) -> str:
    ordered = sorted(
        results.items(),
        key=lambda x: (0 if JOURNALS[x[0]]["abs"] == "4*" else 1, x[0]),
    )
    sections: List[str] = []
    for jname, papers in ordered:
        if not papers:
            continue
        info = JOURNALS[jname]
        rows = "".join(
            f'<li style="margin:10px 0;">'
            f'<a href="{p["url"]}" style="color:#0a3161;font-weight:600;'
            f'text-decoration:none;line-height:1.4;">{p["title"]}</a>'
            + (
                f' <span style="color:#999;font-size:12px;font-weight:normal;'
                f'font-family:Arial,sans-serif;">({p["pub_date"]})</span>'
                if p["pub_date"] else ""
            )
            + (
                f'<br><span style="color:#666;font-size:13px;margin-top:2px;'
                f'display:block;">{p["authors"]}</span>'
                if p["authors"] else ""
            )
            + "</li>"
            for p in papers
        )
        count = (
            f'<span style="color:#888;font-size:13px;font-weight:normal;'
            f'margin-left:6px;">({len(papers)} paper{"s" if len(papers)>1 else ""})</span>'
        )
        sections.append(
            f'<div style="margin-bottom:30px;padding-bottom:18px;'
            f'border-bottom:1px solid #e8e8e8;">'
            f'<h2 style="margin:0 0 10px;font-size:16px;'
            f'font-family:Arial,sans-serif;color:#111;">'
            f'<a href="{info["home"]}" style="color:#111;text-decoration:none;">'
            f'{jname}</a>{abs_badge(info["abs"])}{count}</h2>'
            f'<ul style="margin:0;padding-left:18px;">{rows}</ul></div>'
        )

    total = sum(len(p) for p in results.values())
    body  = "\n".join(sections) or '<p style="color:#666;">No new papers this period.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="font-family:Georgia,serif;max-width:740px;margin:0 auto;
             padding:32px 24px;color:#111;background:#fff;line-height:1.6;">

  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:26px;">
    <tr>
      <td>
        <h1 style="margin:0;font-size:24px;color:#0a3161;
                   font-family:Arial,sans-serif;letter-spacing:-0.5px;">
          📄 Economics Journal Briefing
        </h1>
        <p style="margin:6px 0 0;color:#666;font-size:14px;font-family:Arial,sans-serif;">
          {date_label} &nbsp;·&nbsp;
          {total} new paper{"s" if total != 1 else ""} &nbsp;·&nbsp;
          ABS 4* &amp; 4 journals
        </p>
      </td>
    </tr>
  </table>

  <div style="background:#f4f7fb;border-left:3px solid #0a3161;
              padding:10px 14px;margin-bottom:26px;font-size:13px;
              font-family:Arial,sans-serif;color:#444;">
    <strong style="color:#0a3161;">ABS 4*</strong> = World elite &nbsp;|&nbsp;
    <strong style="color:#2c6fad;">ABS 4</strong> = Top-rated &nbsp;|&nbsp;
    Click any title to open the abstract · Click any journal name to visit the journal
  </div>

  {body}

  <p style="margin-top:36px;color:#bbb;font-size:12px;font-family:Arial,sans-serif;
            border-top:1px solid #eee;padding-top:14px;">
    Automated via GitHub Actions · Papers sourced from public RSS feeds ·
    <a href="https://github.com/junwei-fan/econ-briefing"
       style="color:#bbb;">github.com/junwei-fan/econ-briefing</a>
  </p>
</body>
</html>"""


def send_email(html: str, subject: str) -> None:
    resend.api_key = RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from":    SENDER_EMAIL,
        "to":      [RECIPIENT_EMAIL],
        "subject": subject,
        "html":    html,
    }
    response = resend.Emails.send(params)
    log.info("✓ Email sent via Resend → %s  (id: %s)",
             RECIPIENT_EMAIL, response.get("id", "?"))


def main() -> None:
    cutoff     = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)
    date_label = datetime.now().strftime("%B %d, %Y")
    subject    = f"📄 Economics Journal Briefing — {date_label}"

    tracking = load_tracking()
    sent_ids = set(tracking.keys())
    results: Dict[str, List[dict]] = {}
    new_ids: Dict[str, str]        = {}

    log.info("Fetching RSS feeds (cutoff: %s UTC) …", cutoff.strftime("%Y-%m-%d"))
    for jname, jinfo in JOURNALS.items():
        papers = fetch_journal(jname, jinfo, cutoff, sent_ids)
        if papers:
            results[jname] = papers
            ts = datetime.now(timezone.utc).isoformat()
            for p in papers:
                new_ids[p["id"]] = ts
        time.sleep(REQUEST_DELAY)

    total = sum(len(v) for v in results.values())
    log.info("New papers: %d across %d journal(s).", total, len(results))

    if total == 0:
        log.info("Nothing new — no email sent.")
        save_tracking(prune_tracking(tracking))
        return

    html = build_html(results, date_label)
    send_email(html, subject)

    tracking.update(new_ids)
    save_tracking(prune_tracking(tracking))


if __name__ == "__main__":
    main()

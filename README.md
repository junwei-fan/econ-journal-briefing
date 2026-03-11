# 📄 Economics Journal Briefing

> Automatically email yourself new papers from top economics journals — weekly or monthly, fully free, no server required.

Fetches new papers from **28 ABS 4★ and ABS 4 economics journals** via public RSS feeds and sends you a clean, formatted HTML email. Runs entirely on GitHub Actions — no computer needs to be on, no subscriptions, no passwords stored.

---

## What the email looks like

```
📄 Economics Journal Briefing — March 10, 2026
23 new papers · ABS 4* & 4 journals

American Economic Review  [ABS 4★]  (2 papers)
  • Paper Title One (3 Mar 2026)
    Author A, Author B
  • Paper Title Two (5 Mar 2026)
    Author C, Author D

Management Science  [ABS 4★]  (4 papers)
  • ...

Journal of Public Economics  [ABS 4]  (1 paper)
  • ...
```

Every title is a live hyperlink directly to the abstract on the publisher's website.

---

## Journals included (28 total)

| Rating | Journals |
|--------|---------|
| **ABS 4★** | American Economic Review, Econometrica, Journal of Political Economy, Quarterly Journal of Economics, Review of Economic Studies, Management Science, Journal of Finance, Review of Financial Studies, Journal of Financial Economics |
| **ABS 4**  | AEJ: Applied Economics, AEJ: Economic Policy, AEJ: Macroeconomics, AEJ: Microeconomics, Economic Journal, International Economic Review, Journal of Applied Econometrics, Journal of Development Economics, Journal of Econometrics, Journal of Economic Literature, Journal of Economic Perspectives, Journal of Economic Theory, Journal of Human Resources, Journal of International Economics, Journal of Labor Economics, Journal of Monetary Economics, Journal of Public Economics, RAND Journal of Economics, Review of Economics and Statistics |

---

## Setup (one-time, about 10 minutes)

### Step 1 — Fork this repository

Click the **Fork** button at the top-right of this page.

> ⚠️ **Set your fork to Private.**
> After forking, go to your fork → **Settings → scroll to the bottom → Change repository visibility → Make private.**
> This prevents GitHub from disabling the scheduled workflow after 60 days of inactivity (which only affects public repos).

---

### Step 2 — Get a free Resend API key

Resend is a free email delivery service. No password is ever stored — only a revocable API key.

1. Go to **[resend.com](https://resend.com)** and sign up — free, no credit card needed
2. In the dashboard, click **API Keys → Create API Key**
3. Name it anything (e.g. `journal-briefing`), permission: **Sending access** → click **Add**
4. **Copy the key shown** — it starts with `re_` and you only see it once

> **Important:** When using the free `onboarding@resend.dev` sender, Resend only allows sending to the email address you signed up with. So use the same email for both Resend signup and the `RECIPIENT_EMAIL` secret below.

---

### Step 3 — Add two GitHub Secrets

In your forked repository:

**Settings → Secrets and variables → Actions → New repository secret**

Add these two secrets exactly as shown:

| Name | Value |
|------|-------|
| `RESEND_API_KEY` | Your key from Step 2 (e.g. `re_abc123xyz`) |
| `RECIPIENT_EMAIL` | The email you signed up to Resend with |

---

### Step 4 — Test it

1. In your repo, click the **Actions** tab
2. Click **Economics Journal Briefing** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Wait about 60 seconds, then check your inbox

✅ If you see the email, you're done — it will now run automatically on your chosen schedule.

---

## Customisation

### Remove journals you don't want

Open `briefing.py` in your repo (click the file, then the pencil ✏️ icon to edit).

Find the journal you want to remove and add `#` at the start of each of its 4 lines:

**Before (journal is included):**
```python
    "Journal of Finance": {
        "rss":  "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
        "home": "https://onlinelibrary.wiley.com/journal/15406261",
        "abs":  "4*",
    },
```

**After (journal is removed):**
```python
#    "Journal of Finance": {
#        "rss":  "https://onlinelibrary.wiley.com/feed/15406261/most-recent",
#        "home": "https://onlinelibrary.wiley.com/journal/15406261",
#        "abs":  "4*",
#    },
```

Commit the change. Done.

---

### Change the schedule

Open `.github/workflows/briefing.yml` and find this line:

```yaml
    - cron: "0 7 * * 1"   # ← CHANGE THIS LINE to set your schedule
```

Replace the cron expression with your preferred schedule:

| Cron expression | Meaning |
|----------------|---------|
| `"0 7 * * 1"` | Every **Monday** at 07:00 UTC *(default)* |
| `"0 1 * * 1"` | Every **Monday** at 01:00 UTC = **9am Beijing / Hong Kong** |
| `"0 9 * * 1"` | Every **Monday** at 09:00 UTC = **9am London** |
| `"0 14 * * 1"` | Every **Monday** at 14:00 UTC = **9am New York** |
| `"0 7 1 * *"` | **1st of every month** at 07:00 UTC |
| `"0 7 1,15 * *"` | **1st and 15th** of every month |

> Use **[crontab.guru](https://crontab.guru)** to build any custom schedule.

If switching to **monthly**, also open `briefing.py` and change:
```python
DAYS_LOOKBACK = int(os.getenv("DAYS_LOOKBACK", "8"))
```
to:
```python
DAYS_LOOKBACK = int(os.getenv("DAYS_LOOKBACK", "32"))
```

---

### Add a journal not on the list

In `briefing.py`, copy any existing journal block and update the 4 values:

```python
    "Your Journal Name": {
        "rss":  "https://the-journals-rss-feed-url",
        "home": "https://the-journal-homepage",
        "abs":  "4",   # label only — change to whatever rating you want
    },
```

To find a journal's RSS feed URL, look for an RSS icon on the journal's website, or search `[journal name] RSS feed`.

---

## How deduplication works

After every successful run, the script saves all sent paper URLs to `sent_papers.json` and commits it back to your repo. On the next run, any URL already in that file is skipped — so you will never receive the same paper twice, even if you run it manually multiple times.

**To reset and receive everything again:** edit `sent_papers.json`, replace all contents with `{}`, and commit.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No email received | Check the Actions log for errors. Check your spam folder. |
| `403` error from Resend | Your `RECIPIENT_EMAIL` secret must match the email you used to sign up to Resend |
| Workflow not running on schedule | GitHub can delay runs up to 30 min. If it never runs, check the repo has been active in the last 60 days, or re-enable via Actions → Enable workflow |
| Some journals show 0 papers | Quarterly journals may have no new papers that week — this is normal |
| Feed error warnings in log | Minor RSS formatting issues — harmless, the journal is still checked |

---

## Files

| File | Purpose |
|------|---------|
| `briefing.py` | Main script — edit this to add/remove journals |
| `.github/workflows/briefing.yml` | Workflow — edit this to change the schedule |
| `sent_papers.json` | Tracks sent papers for deduplication — do not delete |

---

*Papers sourced from public RSS feeds. This tool does not scrape, reproduce, or redistribute any copyrighted content — it only collects titles, authors, and links that publishers make freely available via RSS.*

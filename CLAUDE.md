# Internship Watcher

Polls job boards on a schedule and emails John the moment a new relevant
internship opens, plus a twice-weekly digest of competitions, scholarships and
programs.

**Retargeted 2026-09-07.** This repo was previously configured for a different
student (Georgia Tech, May 2028, active Secret clearance, a Summer 2027 quant
offer already in hand, a semester in Madrid). All of that drove the filtering,
the email layout and the docs. It has been rewritten for John's situation — if
you find a stale reference to "Alex", NYC-quant-first ranking, or a Madrid
season block, it's a leftover: fix it rather than working around it.

## CURRENT MODE

1. **Hourly role sweep — full width.** Summer 2027 cycle, five lanes, US and
   international. The `top_firms_only` / `fall_2027_only` narrowing gates in
   `config.json → filters` are both **off**; so is `us_only`. Nothing is
   restricted to elite quant firms any more.
2. **Wed + Sun 14:00 UTC opportunities digest** (see "Opportunities digest").

Expect the hourly sweep to be quiet outside peak season. Summer-2027 postings
open in waves from roughly August 2026 through winter; a run that reports zero
new roles is normal, a run that reports zero *sources resolved* is a bug — read
the Actions log.

## Who this is for (drives all filtering)

- **Georgia Tech, B.S. Computer Science**, Artificial Intelligence and
  Cybersecurity threads, Minor in Leadership Studies. **Graduating May 2029**,
  so Summer 2027 is his rising-junior internship.
- **Five lanes, hunted in parallel** — the email and `TOP_PICKS.md` group roles
  into these, in the order set by `filters.lane_order`:

  | Lane | What lands here |
  |---|---|
  | `ai` | ML, deep learning, applied/research science, CV, NLP, LLM, robotics |
  | `cyber` | security engineering, appsec, detection, offensive security, crypto |
  | `quant` | quant dev / research / trading, or any role at a known quant firm |
  | `startup` | anything from a config source tagged `"lane": "startup"` |
  | `swe` | general software: backend, platform, infra, full-stack, mobile |
  | `other` | matched the filters but fits none of the above |

  Reordering the email is a one-line edit to `lane_order` — no code change.
- **Relevant background** for tailoring applications: co-founded RISEE Finance
  (nonprofit iOS financial-management app, Swift/SwiftUI, in beta) and Volee
  (iOS app for competitive tennis matchmaking); built Python GUI automation
  tools used by engineering teams at John Deere (Mar 2025 – Jan 2026, sole
  developer, still in use). Campus: GreyHat, Competitive Programming (CP@GT),
  Quantum Computing club, DIB Cyber Compliance VIP, Study Abroad Peer Advisor.
  Completed the Leadership for Social Good program in Budapest (Cowan
  Scholarship).
- **US and international.** `filters.us_only` is `false`, so non-US postings
  reach the email. `_is_us_location()` and `NON_US_RE` still exist — flip
  `us_only` to `true` to go US-only again.
- **Defense and national-lab sources are kept** (Lockheed, L3Harris, Leidos,
  Booz Allen, GDMS, Northrop, RTX, MIT LL, JHU APL, Sandia, GTRI, USAJOBS).
  Many of those internships require US citizenship and some require a
  clearance; `is_clearance()` tags them for the run log but no longer creates
  its own email section. **Check eligibility on each posting before applying** —
  the watcher does not know John's clearance status and does not assume one.
- **Summer 2027 only.** `filters.years = ["2027"]`; fall/spring/winter 2027 and
  the 2026/2028 cycles are excluded by title and by `reject_cycle_phrases`.

## Opportunities digest — Wed + Sun

Cron `0 14 * * 0,3` → `DIGEST_MODE=1` → `send_weekly_digest()`. **Every send is
the COMPLETE current list**, not a diff — the point is that you can paste one
email into an AI and ask what's best without opening an older one. Sections:

1. **NEW since last send** — new `opportunities.json` entries, watched pages
   that changed, discovery-feed hits.
2. **Everything currently open** — every entry in `opportunities.json` whose
   deadline/event hasn't passed, sorted by deadline, "closing ≤10d" pulled out.
   `filters.hide_seasons` is **empty** (John is on campus year-round); set it to
   `["spring"]` if a semester abroad ever comes up, and in-person events that
   season will be hidden while online ones stay.
3. **Discovery feed** — new items from `ats: "rss"` sources (Google News query
   feeds, Reddit r/quant, HN) via `fetch_rss()`, keyword-gated by
   `watch_keywords`. Unverified; promote good ones into `opportunities.json`.
   First read of a feed is a silent baseline (`rssfeed::<url>` marker) so a new
   feed can't flood.
4. Index of every watched page.

`opportunities.json` is the structured source of truth (id, dates ISO, format,
season, travel, prizes, perks, eligibility). **Hand-curated** — pagewatch only
says "a page changed"; it can't extract dates. When something is found (or a
watched page fires), add an entry.

A source is in the digest iff `_is_digest_source()`: explicit `"digest": true`
wins, else the `name:` prefix ∈ Event/Competition/Hackathon/Scholarship/
Fellowship/Abroad/Program/NatSec/Lab/GT/Conference/Grant/RSS. Company job
boards (`Quant SPA:`, `Page:`, `Firm SPA:`, `Cyber:`, `Startup:`) stay OUT —
that's the hourly sweep.

**Not feasible (don't retry):** LinkedIn (no API, scraping blocked from
runners), Discord (needs a bot token in each server), Reddit beyond r/quant
(429s from CI), Devpost RSS (406), Meta/Citadel-students/Correlation One pages
(bot-blocked).

**Pagewatch keying (gotcha #9):** pagewatch state keys are
`pw::<url>::#<content-hash>` via `_pw_key()`. Keyed by URL alone, a watcher
fires **exactly once, ever**, then goes silent — so "tell me when applications
open" never fires again. The dedicated prefix also avoids colliding with job
URLs containing `#` fragments. A URL with no recorded hash yet is baselined
**silently**, so a keying change can't flood the first email.

## Layout

| File | Purpose |
|---|---|
| `.github/workflows/watch.yml` | Hourly sweep + Wed/Sun digest + manual run button (modes: internships / digest / verify) |
| `watcher.py` | All logic. Fetchers → filters → lanes → dedup → email |
| `config.json` | Sources + filters. **Most changes belong here, not in code.** |
| `verify_sources.py` | Probes every direct-ATS token and reports which are dead. Run after adding sources. |
| `seen_jobs.json` | State. Auto-committed each run. Never hand-edit. |
| `OPEN_ROLES.md` | Auto-generated snapshot of open roles, rewritten each full sweep. Page-change pings live in their own section at the bottom. Never hand-edit. |
| `TOP_PICKS.md` | Auto-generated, ranked by lane. Never hand-edit. |
| `opportunities.json` | Hand-curated competitions/programs feeding the digest |
| `PROGRAMS.md` | Human-readable calendar of competitions, scholarships, research |
| `apply.md` | Slash-command pipeline: tailor a resume to a posting and log it |
| `applications.md` | **Private, gitignored** (repo is public). Application tracker. Never commit it. |

**Secrets (repo → Settings → Secrets → Actions):** `SMTP_USERNAME` (a Gmail
address), `SMTP_PASSWORD` (Gmail **App Password**, not the account password),
`EMAIL_TO` (John's inbox). Optional: `USAJOBS_API_KEY` + `USAJOBS_EMAIL`.

## Architecture

Every entry in `config.json → firms[]` has an `ats` field routing it to a
fetcher in `watcher.py`'s `FETCHERS` dict. Every fetcher returns normalized
dicts: `{id, title, company, location, url, content, ...}`. An entry may also
carry `"lane": "<lane>"`, which overrides title-based lane inference for every
role from that source — that's how the `startup` lane is expressed, since
"startup" isn't something you can read off a job title.

| `ats` | What it does |
|---|---|
| `greenhouse` `lever` `ashby` `smartrecruiters` `workable` | Public ATS JSON APIs. `token` = the slug in the board URL. |
| `workday` | Undocumented-but-public CXS endpoint. Needs `host` / `tenant` / `site` — get them from the careers page's DevTools → Network → the POST to `/wday/cxs/.../jobs`. Use `search_text` to filter server-side and `max_pages` to cap. |
| `amazon` | Undocumented `amazon.jobs/en/search.json`. Covers AWS / Robotics / all. |
| `usajobs` | Federal: NASA, DOE labs, NSA, Army/Navy research, Pathways. Needs a free key. |
| `github_json` | Tracker repos publishing `listings.json` (vanshb03). |
| `github_md` | Tracker repos whose data is a markdown **table** (sndsh404, speedyapply). |
| `nuft` | Parses the NUFT quant README for board links, then polls them. |
| `autodiscover` | **The big one.** Harvests every apply URL from all trackers, decodes each company's ATS board, and polls ~211 boards **in parallel**. Self-expanding: any company a tracker adds gets polled from then on. |
| `pagewatch` | Change-detector for feed-less pages. Alerts when watched keywords appear/change. **Not a job source** — see gotcha #10. |
| `rss` | Google News / Reddit / HN query feeds for the digest's discovery section. |

Failed sources are **skipped and logged** (`x <name> skipped`), never crash the
run. Read the Actions log to see which sources actually resolved.

## Filtering (`config.json → filters`)

1. `title_keywords` — must look like an internship
2. `title_require_any` — must be a CS/math/security domain (~89 keywords)
3. `title_exclude` — PhD/Masters, wrong cycle, non-CS engineering
4. **Cycle check** — see gotcha #1
5. `us_only` — **off**. When on, `_is_us_location()` drops clearly-non-US roles
   after the relevance check; empty/ambiguous locations are always kept
6. `top_firms_only` / `fall_2027_only` — **both off**, kept for future use
7. `clearance_keywords` — computed by `is_clearance()` for the run log only

## HARD-WON GOTCHAS — read before changing anything

1. **NEVER require the year in the job title.** Most companies don't put it
   there (Palantir: `"Forward Deployed Software Engineer - Internship - Intel"`).
   An earlier version required `"2027"` in the title and **silently discarded
   every such role** across all direct ATS sources for weeks.
   Current logic: if the title names *any* year, one of them must be ours; else
   check the description; **if no year appears anywhere, KEEP it** — a live
   intern posting is almost always the current cycle, since recruiting runs a
   year ahead.

2. **Silent drops are the most dangerous bug class.** #1 went unnoticed because
   a filtered-out role produces no log line. **If you add a filter, log what it
   drops.**

3. **Auto-discovery must stay parallel.** 211 boards polled sequentially takes
   *hours* (Workday paginates 20 at a time). Keep `ThreadPoolExecutor`,
   `max_pages=3`, and `budget_seconds`. A sequential version hung a run 20+ min.

4. **`git push` must rebase first.** The `Save state` step does
   `git pull --rebase` before pushing — otherwise editing files via the GitHub
   web UI moves `main` and the run's state-commit fails non-fast-forward.

5. **Community trackers go stale.** `sharunkumar` is really a *2026* repo; its
   few "2027" tags produced dead links and closed roles. It's disabled.
   **Verify a tracker's actual cycle before enabling it.**

6. **Trackers lag; boards don't.** Polling a company's board directly beats
   reading a tracker. That's the whole point of `autodiscover`.

7. **Substring keyword matching floods the email with garbage.** `"intern" in
   title` matches Intern**al**, Intern**ational**, Intern**et** — one baseline
   email had 100+ "Internal Audit" directors. Same trap: `"systems"` matched
   "Eco**systems**". `_title_is_internship()` and `_has_term()` use
   word-boundary regexes; keep it that way for any new keyword gate. Filters
   count every drop by reason (`DROP_COUNTS`) and print a summary each run.

8. **Emails show one line per role.** `_collapse_locations()` merges the same
   company+title posted in N cities into one entry ("NYC · Palo Alto +2 more").
   Display-only: every posting URL is still tracked individually in
   `seen_jobs.json`.

9. **Pagewatch keying** — see "Opportunities digest" above.

10. **A pagewatch hit is not a job.** It only means "this page's HTML changed".
    Before 2026-09-07 those alerts flowed into `OPEN_ROLES.md` and
    `TOP_PICKS.md` as if they were postings — the file claimed "19 open roles"
    when all 19 were change pings with the title "Page changed - check ...".
    `_lane()` now routes anything with `pagewatch: true` into the `watch` lane,
    `write_top_picks()` skips them outright, and `write_open_roles()` counts
    them separately. Don't undo that.

11. **`\bsecurity\b` in `CYBER_RE` is word-bounded on purpose.** Without the
    boundary, every trading firm with "Securities" in its name lands in the
    cyber lane.

12. **A wrong ATS token fails silently-ish.** `fetch_*` raises, main() prints
    `x <name> skipped`, the run continues — correct at runtime, but a dead
    source can sit in config for months. The `Cyber:` and `Startup:` entries
    added 2026-09-07 carry `"verified": false` because the tokens were guessed,
    not confirmed. **Run `python3 verify_sources.py` (or the workflow's
    `verify` mode) and delete whatever 404s.**

## Pending / next upgrades

- **SimplifyJobs/Summer2027-Internships — ADDED 2026-09-09** as a `github_json`
  source and as the first `autodiscover` seed. ~1,400 active Summer-2027
  listings across ~350 companies, updated daily; by far the biggest source.
  `skip_categories` drops Hardware/Product; `lane_by_category` maps
  Quant→quant and AI/ML/Data→ai. The older `vanshb03` tracker had 0 active
  2027 entries that day and is kept only in case it revives. Any source can set
  `silent_baseline: true` to be recorded without a catch-up email on first poll.
- **Verify the 16 unverified sources** added 2026-09-07 (gotcha #12).
- **USAJOBS is configured but inert** until `USAJOBS_API_KEY` / `USAJOBS_EMAIL`
  secrets are set. Free key: <https://developer.usajobs.gov/apirequest/>
- **iCIMS fetcher** — several defense contractors (GD Mission Systems) use it;
  no clean public API, so they're `pagewatch` only right now.
- **Eightfold fetcher** — Netflix and others.
- **FAANG page-watchers are weak** (JS single-page apps). Set *native* job
  alerts at Google / Meta / Apple / Microsoft / Netflix as the real backup.
- **GT-specific sources are thin.** CareerBuzz/Handshake has no public API, but
  GT club mailing lists (GreyHat, CP@GT) surface things nothing here polls.
- LinkedIn / Indeed have **no public API** and scraping gets IP-blocked from
  Actions runners. They mostly re-list ATS postings anyway. Don't go there.

## Testing

Filters are pure functions — test them without any network:

```bash
python3 -c "
import json, watcher
f = json.load(open('config.json'))['filters']
job = {'title': 'Software Engineer Intern', 'location': 'NYC', 'content': ''}
print(watcher.is_relevant(job, f))            # True
print(watcher._lane(job, 'Figma', job['title']))  # swe
"
```

Check every ATS token resolves:

```bash
pip install -r requirements.txt
python3 verify_sources.py
```

Full local run (sends a real email):

```bash
SMTP_USERNAME=... SMTP_PASSWORD=... EMAIL_TO=... python watcher.py
```

Delete `seen_jobs.json` locally to force a fresh baseline. **Don't commit that
deletion** unless you want a full catch-up email.

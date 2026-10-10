#!/usr/bin/env python3
"""Stage-1 Jev triage over the watcher's generated role lists.

Parses TOP_PICKS.md / OPEN_ROLES.md, asks Jev four typed questions per posting
(lane, relevance, grad-only, is-engineering; cycle in code), and writes a ranked shortlist.

Jev sees only company + title + location -- the same public text already in the
markdown file. No private file (career-history.md, applications.md) is sent.

    ./jev_triage.py --dry-run                 # parse only, no API call
    ./jev_triage.py --limit 40                # try a small slice first
    ./jev_triage.py --source OPEN_ROLES.md    # the full 3.7k board
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
# Scratch output + caches live in .jev/ so the repo root stays readable.
DATA = os.path.join(HERE, ".jev")
os.makedirs(DATA, exist_ok=True)
# John's private tracker lives in job-search/ (gitignored).
APPLICATIONS = os.path.join(HERE, "job-search", "applications.md")
HELPER = os.path.expanduser("~/.claude/skills/jev/scripts/jev.py")

# Resume lanes, named exactly as resumes/lanes/ names them -- the answer is used
# to pick a template file, so these strings have to match that directory.
LANES = {
    "startup": "Small team, startup, full-stack, forward-deployed, or 'build it from scratch' engineering.",
    "ai-ml": "Machine learning, deep learning, applied science, research science, computer vision, NLP, LLM, or robotics.",
    "data": "Data science, data engineering, analytics, or business intelligence.",
    "cyber": "Security engineering, application security, detection, offensive security, cryptography, or security compliance.",
    "swe-devops": "General software engineering: backend, platform, infrastructure, DevOps, SRE, mobile, or full-stack at a larger company.",
    "quant": "Quantitative research, quantitative development, or trading, or an algorithm-heavy engineering role at a trading firm.",
    "not_a_fit": "Not a software, data, security, or quantitative role at all. Accounting, banking operations, supply chain, manufacturing, hardware, mechanical, civil, marketing, HR, sales, legal, or clinical.",
}

RELEVANCE = [
    "Not a software, data, security, or quantitative role.",
    "An engineering role in a specialty outside the candidate's background: FPGA, RF, ASIC, chip design, embedded firmware, electrical hardware, or mechanical design.",
    "Software-adjacent but not engineering work: IT support, manual QA testing, technical sales, product management, or business analysis.",
    "A general software engineering role whose title does not name a specialty, such as Software Engineer Intern or Software Development Engineer Intern, including ones on a named team like robotics or payments.",
    "The title names one of the candidate's strengths: iOS or mobile development, machine learning or AI engineering, data science or data engineering, security engineering, or quantitative research or development.",
]

# Cycle is decided in code, not by Jev: year and season words are literal text,
# and Jev's docs list date handling as a weak spot. Only a title that names
# another year, an off-season term, or non-summer months gets cut.
OTHER_TERM = re.compile(r"\b(winter|fall|autumn|spring)\b", re.I)
OFF_MONTHS = re.compile(r"\b(january|february|march|april|september|october|november|december)\b", re.I)


def cycle_of(title):
    years = set(re.findall(r"\b20\d\d\b", title))
    if years and "2027" not in years:
        return "different_cycle"
    if OTHER_TERM.search(title) or OFF_MONTHS.search(title):
        return "different_cycle"
    return "summer_2027" if "2027" in years else "not_stated"

# "- [company — Title](url) 🇺🇸 — Location"  (the flag emoji is optional)
# 2026-10-10: TOP_PICKS lane lines now start with a fit badge like `3.8` (watcher fit scores, 2026-10-01).
ENTRY = re.compile(r"^-\s+(?:`[^`]*`\s+)?(?:\*\*[^*]+\*\*\s+—\s+)?\[([^\]]+)\]\((https?://[^)]+)\)(.*)$")


def load_helper():
    spec = importlib.util.spec_from_file_location("jev_helper", HELPER)
    if spec is None or not os.path.exists(HELPER):
        sys.exit(f"helper not found at {HELPER}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm_url(url):
    """Same posting, different URL spellings: locale segment, query string,
    trailing /application, trailing slash."""
    u = url.split("#")[0].split("?")[0].rstrip("/")
    u = re.sub(r"/[a-z]{2}-[A-Za-z]{2}(?=/)", "", u)
    u = re.sub(r"/application$", "", u)
    return u.lower()


def parse(path, limit=None):
    """Pull (company, title, location, url) out of a generated roles file."""
    postings, seen = [], set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = ENTRY.match(line.rstrip())
            if not m:
                continue
            label, url, tail = m.groups()
            if "—" in label:
                company, title = label.split("—", 1)
            else:
                company, title = "", label
            location = tail.split("—", 1)[1].strip() if "—" in tail else ""
            key = norm_url(url)
            if key in seen:
                continue
            seen.add(key)
            postings.append({
                "company": company.strip(),
                "title": title.strip(),
                "location": location.strip(),
                "url": url,
            })
            if limit and len(postings) >= limit:
                break
    return postings


def build_request(p, model):
    return {
        "model": model,
        "state": {"company": p["company"], "title": p["title"], "location": p["location"]},
        "questions": {
            "lane": {
                "type": "choice",
                "instructions": "Which resume lane best fits this job posting, judging only from the company, title, and location?",
                "criteria": LANES,
            },
            "relevance": {
                "type": "score",
                "instructions": (
                    "How well does this role match a Georgia Tech computer science student "
                    "with AI and cybersecurity threads, whose experience is iOS app development "
                    "in Swift, Supabase backends, applied machine learning in Python, and "
                    "security engineering?"
                ),
                "criteria": RELEVANCE,
            },
            "grad_only": {
                "type": "noul",
                "instructions": "The title says this internship is only for graduate students (master's or PhD).",
                "criteria": {
                    "true": "The title says Grad, Graduate, Master's, MS, PhD, or Doctoral intern.",
                    "false": "The title says Undergrad, or does not mention a degree level.",
                },
            },
            "is_engineering": {
                "type": "noul",
                "instructions": "This posting is for a software, data, security, or quantitative role.",
                "criteria": {
                    "true": "The role's main work is writing software, building data systems, security engineering, or quantitative research, development, or trading.",
                    "false": "The role's main work is something else: accounting, banking operations, audit, supply chain, manufacturing, hardware, mechanical, civil, marketing, HR, sales, legal, or clinical.",
                },
            },
        },
    }


# ---- Stage 2: John's hard rules, checked against the posting text itself ----
# 1. Cut roles only for graduate students, postdocs, or finished degrees.
# 2. Cut non-US roles that need existing local work authorization (John is
#    authorized to work in the US only, and wants roles abroad).
# Only the sentences that mention degrees or work authorization are sent to
# Jev: Jev's docs say irrelevant text lowers accuracy, and it keeps requests
# small. A posting that can't be read or says nothing is KEPT, never dropped.
DEGREE_RE = re.compile(r"bachelor|undergrad|master'?s|\bph\.?d|doctora|post-?doc|graduate|degree|"
                       r"enrolled|\bstudents?\b|class of|year of study|\bB\.?S\.?\b|\bM\.?S\.?\b", re.I)
AUTH_RE = re.compile(r"authori[sz]|visa|sponsor|right to work|work permit|eligib|citizen|"
                     r"residen|legally|immigration", re.I)

DEGREE = {
    "undergrad_ok": "Current bachelor's or undergraduate students are eligible, alone or alongside Master's or PhD students, or any current student is eligible with no degree-level restriction.",
    "grad_only": "Only current Master's or PhD students are eligible. Undergraduates are not.",
    "graduated_or_postdoc": "Requires an already-completed degree, a completed PhD, or postdoctoral experience, so current undergraduates are not eligible.",
    "not_stated": "The excerpts do not say which degree levels are eligible.",
}
WORK_AUTH = {
    "must_already_be_authorized": "The candidate must already have the legal right to work in the country where the job is located, or the posting says it will not sponsor a visa or work permit.",
    "sponsorship_or_open": "The posting says it will sponsor a visa or work permit, or that it welcomes international candidates who need one.",
    "not_stated": "The excerpts say nothing about work authorization, visas, or sponsorship.",
}


def excerpts(text, limit=2000):
    """Sentences about degree level and about work authorization, each with its
    own budget so a long degree section can't crowd out the visa sentence."""
    deg, auth, seen = [], [], set()
    for raw in re.split(r"\n|(?<=[.;])\s+(?=[A-Z])", text):
        line = raw.strip()[:400]
        if len(line) < 12 or line in seen:
            continue
        seen.add(line)
        if AUTH_RE.search(line) and sum(map(len, auth)) < limit:
            auth.append(line)
        elif DEGREE_RE.search(line) and sum(map(len, deg)) < limit:
            deg.append(line)
    return deg + auth

def verify(rows, helper, key, is_us, model, concurrency, overrides=None):
    overrides = overrides or {}
    import jd_fetch

    def one(r):
        text, src = jd_fetch.fetch_jd(r["url"])
        ex = excerpts(text) if text else []
        abroad = not is_us(r["location"])
        r = dict(r, jd_source=src, abroad=abroad, excerpts=ex)
        qs = {}
        if any(DEGREE_RE.search(l) for l in ex):
            qs["degree"] = {"type": "choice",
                            "instructions": "Which students does this internship posting say are eligible?",
                            "criteria": DEGREE}
        if abroad and any(AUTH_RE.search(l) for l in ex):
            qs["work_auth"] = {"type": "choice",
                               "instructions": "What does this posting say about the legal right to work in the job's country?",
                               "criteria": WORK_AUTH}
        if not qs:
            return dict(r, degree="not_stated" if text else "unreadable", work_auth=None, cost=0.0)
        resp, _, err = cached_call(helper, {"model": model, "questions": qs,
                                    "state": {"title": r["title"], "location": r["location"], "posting_excerpts": ex}}, key)
        if err:
            return dict(r, degree="error", work_auth=None, error=err.splitlines()[0], cost=0.0)
        a = resp["answers"]
        return dict(r,
                    degree=a["degree"]["choice"] if "degree" in a else "not_stated",
                    degree_conf=a["degree"]["confidence"] if "degree" in a else None,
                    work_auth=a["work_auth"]["choice"] if "work_auth" in a else None,
                    auth_conf=a["work_auth"]["confidence"] if "work_auth" in a else None,
                    cost=resp.get("usage", {}).get("cost") or 0.0)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        done = []
        for i, r in enumerate(pool.map(one, rows), 1):
            done.append(r)
            if i % 100 == 0 or i == len(rows):
                print(f"  verified {i}/{len(rows)}", flush=True)

    kept, removed, review = [], [], []
    for r in done:
        o = overrides.get(norm_url(r["url"]), {})
        grad_cut = r["degree"] in ("grad_only", "graduated_or_postdoc") and not o.get("degree_ok")
        auth_cut = r["work_auth"] == "must_already_be_authorized" and not o.get("auth_ok")
        ex = " ".join(r["excerpts"])
        quiet_grad = (not grad_cut and not o.get("degree_ok") and (r.get("degree_conf") or 1) < 0.5
                      and re.search(r"ph\.?d|master'?s|graduate (student|degree)", ex, re.I)
                      and not re.search(r"bachelor|undergrad", ex, re.I))
        unsure = ((grad_cut and (r.get("degree_conf") or 0) < 0.5)
                  or (auth_cut and (r.get("auth_conf") or 0) < 0.5) or bool(quiet_grad))
        if unsure:
            review.append(r)
        elif grad_cut or auth_cut:
            removed.append(dict(r, why="grad/postdoc only" if grad_cut else "needs local work authorization"))
        else:
            kept.append(r)
    return kept, removed, review, done


ANSWER_CACHE = os.path.join(DATA, "jev_cache")


def cached_call(helper, payload, key):
    """Jev answers for an unchanged request are reused, so re-runs are free and
    borderline items don't flip between runs. Change a question's wording and
    its hash changes, so it gets re-asked."""
    import hashlib
    os.makedirs(ANSWER_CACHE, exist_ok=True)
    path = os.path.join(ANSWER_CACHE, hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20] + ".json")
    try:
        resp = json.load(open(path))
        return dict(resp, usage=dict(resp.get("usage", {}), cost=0.0)), 0.0, None
    except (OSError, ValueError):
        pass  # missing or unreadable -> ask Jev again
    resp, elapsed, err = helper.call(payload, key)
    if resp:
        atomic_json(path, resp)
    return resp, elapsed, err


def atomic_json(path, obj):
    """Identical requests can run on two threads at once (same posting text
    under two URLs); write-then-rename so a reader never sees half a file."""
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="TOP_PICKS.md")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample", type=int, help="random N postings instead of the first N")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", default="typesafe/jev-1.13")
    ap.add_argument("--out", default="SHORTLIST.md")
    ap.add_argument("--jsonl", default="jev_triage_raw.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-rank", action="store_true", help="skip stage 3 (priority tiers and closing dates)")
    ap.add_argument("--no-verify", action="store_true", help="skip stage 2 (reading each posting for your hard rules)")
    a = ap.parse_args()

    src = a.source if os.path.isabs(a.source) else os.path.join(HERE, a.source)
    postings = parse(src, None if a.sample else a.limit)
    if a.sample:
        import random
        random.Random(a.seed).shuffle(postings)
        postings = postings[:a.sample]
    print(f"parsed {len(postings)} unique posting(s) from {os.path.basename(src)}")
    if not postings:
        return 1

    if a.dry_run:
        req = build_request(postings[0], a.model)
        print("\nsample state:", json.dumps(req["state"], indent=2))
        print(f"\nquestions per request: {len(req['questions'])}"
              f"  ({', '.join(req['questions'])})")
        print(f"request JSON size: ~{len(json.dumps(req))} chars"
              f"  -> ~{len(json.dumps(req)) // 4} tokens each")
        print(f"estimated total input tokens: "
              f"~{len(postings) * len(json.dumps(req)) // 4:,}")
        print("\nfirst 5 parsed:")
        for p in postings[:5]:
            print(f"  {p['company']:<28} | {p['title'][:52]:<52} | {p['location'][:30]}")
        return 0

    helper = load_helper()
    key = helper.get_api_key()
    results, t0 = [], time.perf_counter()

    def run(p):
        resp, elapsed, err = cached_call(helper, build_request(p, a.model), key)
        return {"posting": p, "response": resp, "elapsed": elapsed, "error": err}

    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        for i, r in enumerate(pool.map(run, postings), 1):
            results.append(r)
            if i % 25 == 0 or i == len(postings):
                print(f"  {i}/{len(postings)}", flush=True)
    wall = time.perf_counter() - t0

    ok = [r for r in results if r["response"]]
    failed = [r for r in results if r["error"]]
    if failed:
        print(f"\n{len(failed)} call(s) failed. First error:\n{failed[0]['error']}",
              file=sys.stderr)
    if not ok:
        return 1

    with open(os.path.join(DATA, a.jsonl), "w", encoding="utf-8") as fh:
        for r in ok:
            fh.write(json.dumps({"posting": r["posting"], **r["response"]}) + "\n")

    rows = []
    for r in ok:
        ans = r["response"]["answers"]
        rows.append({
            **r["posting"],
            "lane": ans["lane"]["choice"],
            "lane_conf": ans["lane"].get("confidence", 0.0),
            "relevance": ans["relevance"]["score"],
            "rel_conf": ans["relevance"].get("confidence", 0.0),
            "cycle": cycle_of(r["posting"]["title"]),
            "engineering": ans["is_engineering"]["noul"],
            "grad_only": ans["grad_only"]["noul"],
        })
    rows.sort(key=lambda x: -x["relevance"])

    # Claude's earlier calls on cases Jev was unsure about (jev_overrides.json,
    # keyed by normalized URL): {"lane": ...}; {"degree_ok": true} or
    # {"auth_ok": true} clears ONE rule; {"keep": false, "why": ...} cuts outright.
    ov_path = os.path.join(DATA, "jev_overrides.json")
    overrides = json.load(open(ov_path)) if os.path.exists(ov_path) else {}
    for r in rows:
        o = overrides.get(norm_url(r["url"]), {})
        if "lane" in o:
            r["lane"], r["lane_conf"] = o["lane"], 1.0

    cost = sum(r["response"].get("usage", {}).get("cost") or 0 for r in ok)
    tokens = sum(r["response"].get("usage", {}).get("input_tokens") or 0 for r in ok)

    keep = [r for r in rows if r["relevance"] >= 2.5 and r["engineering"] >= 0.5
            and r["cycle"] != "different_cycle" and r["grad_only"] < 0.5]
    removed, review, verify_cost = [], [], 0.0
    w = None
    if not a.no_verify and keep:
        spec_w = importlib.util.spec_from_file_location("watcher", os.path.join(HERE, "watcher.py"))
        w = importlib.util.module_from_spec(spec_w)
        spec_w.loader.exec_module(w)
        print(f"stage 2: reading {len(keep)} posting(s) for your hard rules...")
        t1 = time.perf_counter()
        keep, removed, review, checked = verify(keep, helper, key, w._is_us_location, a.model, a.concurrency, overrides)
        for r in list(review) + list(removed) + list(keep):
            o = overrides.get(norm_url(r["url"]), {})
            if o.get("keep") is not False:
                continue
            for bucket in (review, removed, keep):
                if r in bucket:
                    bucket.remove(r)
            removed.append(dict(r, why=o.get("why", "Claude's call")))
        keep.sort(key=lambda x: -x["relevance"])
        verify_cost = sum(r["cost"] for r in checked)
        cost += verify_cost
        wall += time.perf_counter() - t1
        with open(os.path.join(DATA, a.jsonl.replace(".jsonl", "_verify.jsonl")), "w", encoding="utf-8") as fh:
            for r in checked:
                fh.write(json.dumps(r) + "\n")
        unreadable = sum(1 for r in checked if r["degree"] == "unreadable")
        print(f"  removed {len(removed)} by your rules, {len(review)} for Claude to decide, "
              f"{unreadable} posting(s) unreadable (kept)")

    unsure = [r for r in keep if r["lane_conf"] < 0.5]

    ranked = None
    if not a.no_verify and not a.no_rank and keep:
        import jev_priority
        print(f"stage 3: ranking {len(keep)} role(s) by chance and closing date...")
        t2 = time.perf_counter()
        ranked, rank_cost = jev_priority.prioritize(
            keep, helper, key, cached_call, norm_url, w.extract_deadline, a.model, a.concurrency,
            applications=APPLICATIONS)
        cost += rank_cost
        wall += time.perf_counter() - t2
        with open(os.path.join(DATA, a.jsonl.replace(".jsonl", "_rank.jsonl")), "w", encoding="utf-8") as fh:
            for r in ranked:
                fh.write(json.dumps(r) + "\n")

    def line(r):
        c = r.get("closing", {}).get("label") or "closing date unknown"
        notes = f" · _{', '.join(r['notes'])}_" if r.get("notes") else ""
        fit = "?" if r.get("fit") is None else f"{r['fit']:.1f}"
        return (f"- **{r['lane']}** · fit {fit}/4 · {c} — [{r['company']} — {r['title']}]({r['url']})"
                f" — {r['location']}{notes}\n")

    with open(os.path.join(HERE, a.out), "w", encoding="utf-8") as fh:
        fh.write("# Jev shortlist (auto-generated — do not hand-edit)\n\n")
        fh.write(f"_{len(keep)} kept out of {len(rows)} triaged from "
                 f"{os.path.basename(src)} · {time.strftime('%Y-%m-%d %H:%M')} · "
                 f"{tokens:,} input tokens · ${cost:.5f} · {wall:.0f}s wall._\n\n")
        if ranked:
            fh.write("Tiers combine **fit** (how well your profile meets the posting's required "
                     "qualifications, 0–4), company **selectivity**, title relevance, and class-year "
                     "eligibility. Within a tier, best odds first. `rolling` = no stated deadline; "
                     "it closes when filled, so older postings are the more urgent ones.\n")
            soon = sorted([r for r in ranked if r["tier"] != "applied" and r["closing"]["days_left"] is not None
                           and 0 <= r["closing"]["days_left"] <= 21], key=lambda r: r["closing"]["days_left"])
            if soon:
                fh.write(f"\n## ⏰ Closing within 3 weeks ({len(soon)})\n\n")
                for r in soon:
                    fh.write(f"- **{r['tier']}** · " + line(r)[2:])
            names = [("definitely", "✅ Definitely apply"), ("strong", "👍 Strong"),
                     ("reach", "🎯 Reach — apply, but don't count on it"), ("lower", "Lower priority")]
            for tier, head in names:
                group = sorted([r for r in ranked if r["tier"] == tier], key=lambda r: -r["priority"])
                if not group:
                    continue
                if tier == "lower":
                    fh.write(f"\n<details><summary>{head} ({len(group)})</summary>\n\n")
                else:
                    fh.write(f"\n## {head} ({len(group)})\n\n")
                for r in group:
                    fh.write(line(r))
                if tier == "lower":
                    fh.write("\n</details>\n")
            done_ = [r for r in ranked if r["tier"] == "applied"]
            if done_:
                fh.write(f"\n<details><summary>Already in applications.md ({len(done_)})</summary>\n\n")
                for r in done_:
                    fh.write(line(r))
                fh.write("\n</details>\n")
        else:
            for lane in ["ai-ml", "cyber", "swe-devops", "startup", "data", "quant", "not_a_fit"]:
                group = [r for r in keep if r["lane"] == lane and r not in unsure]
                if not group:
                    continue
                fh.write(f"\n## {lane} ({len(group)})\n\n")
                for r in group:
                    fh.write(f"- **{r['relevance']:.2f}** — [{r['company']} — {r['title']}]({r['url']}) — {r['location']}\n")
        if review:
            fh.write(f"\n## Your rules, but Jev was unsure — Claude decides ({len(review)})\n\n")
            for r in review:
                fh.write(f"- {r['degree']} / {r['work_auth']} — [{r['company']} — {r['title']}]({r['url']}) — {r['location']}\n")
        if unsure:
            fh.write(f"\n## Kept, but Jev was unsure which lane — Claude decides ({len(unsure)})\n\n")
            for r in unsure:
                fh.write(f"- **{r['relevance']:.2f}** (lane conf {r['lane_conf']:.2f} → "
                         f"{r['lane']}) — [{r['company']} — {r['title']}]({r['url']})\n")
        if removed:
            fh.write(f"\n<details><summary>Removed by your rules ({len(removed)})</summary>\n\n")
            for r in removed:
                fh.write(f"- {r['why']} — [{r['company']} — {r['title']}]({r['url']}) — {r['location']}\n")
            fh.write("\n</details>\n")

    print(f"\ntriaged {len(ok)}  kept {len(keep)}  unsure {len(unsure)}")
    print(f"{tokens:,} input tokens   ${cost:.5f}   {wall:.0f}s wall")
    print(f"wrote {a.out} and {a.jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

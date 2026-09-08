#!/usr/bin/env python3
"""
Source verifier
===============
Probes every direct-ATS source in config.json (greenhouse / lever / ashby /
workable / smartrecruiters) and reports which tokens actually resolve.

Why: a wrong token doesn't crash the watcher -- fetch_* raises, main() prints
"x <name> skipped" and moves on. That is the right runtime behaviour, but it
means a dead source can sit in config for months looking fine. Run this after
adding sources, and delete or fix anything it reports as DEAD.

    python3 verify_sources.py            # all direct-ATS sources
    python3 verify_sources.py --unverified   # only ones lacking verified:true

Pagewatch / autodiscover / tracker sources are not probed -- they fail loudly
enough in the run log.
"""
import concurrent.futures as cf
import json
import sys

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
TIMEOUT = 15

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{t}/jobs",
    "lever": "https://api.lever.co/v0/postings/{t}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{t}",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{t}",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{t}/postings",
}


def count(ats, payload):
    if ats == "greenhouse":
        return len(payload.get("jobs", []))
    if ats == "lever":
        return len(payload) if isinstance(payload, list) else 0
    if ats == "ashby":
        return len(payload.get("jobs", []))
    if ats == "workable":
        return len(payload.get("jobs", []))
    if ats == "smartrecruiters":
        return payload.get("totalFound", len(payload.get("content", [])))
    return 0


def probe(firm):
    ats, token = firm.get("ats"), firm.get("token")
    url = URLS[ats].format(t=token)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return ("DEAD", firm, f"HTTP {r.status_code}")
        return ("OK", firm, f"{count(ats, r.json())} posting(s)")
    except Exception as e:  # noqa: BLE001
        return ("DEAD", firm, type(e).__name__ + ": " + str(e)[:80])


def main():
    only_unverified = "--unverified" in sys.argv
    cfg = json.load(open("config.json", encoding="utf-8"))
    firms = [
        f for f in cfg.get("firms", [])
        if f.get("enabled", True) and f.get("ats") in URLS and f.get("token")
        and (not only_unverified or f.get("verified") is not True)
    ]
    print(f"Probing {len(firms)} source(s)...\n")
    results = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(probe, firms):
            results.append(r)

    dead = [r for r in results if r[0] == "DEAD"]
    for status, firm, detail in sorted(results, key=lambda r: (r[0], r[1]["name"])):
        mark = "  ok " if status == "OK" else "  XX "
        print(f"{mark}{firm['name']:<45} {firm['ats']:<16}{firm['token']:<32}{detail}")

    print(f"\n{len(results) - len(dead)} live, {len(dead)} dead.")
    if dead:
        print("\nDead tokens -- fix or delete these entries in config.json:")
        for _, firm, detail in dead:
            print(f"  - {firm['name']} ({firm['ats']}:{firm['token']}) -> {detail}")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())

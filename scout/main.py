"""hacksgiving-scout: find hackathons and startup programs worth Tom's evenings, then tell him.

    python3 -m scout.main run            # one pass: fetch, filter, score, deliver
    python3 -m scout.main run --dry-run  # no delivery, no state change
    python3 -m scout.main loop           # run daily at SCOUT_HOUR (Perth time)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import programs, sources
from .deliver import deliver
from .ideas import idea_for, uncle_says
from .rules import Verdict, evaluate

PERTH = timezone(timedelta(hours=8))
HOME = Path(os.environ.get("SCOUT_HOME", Path.home() / ".scout"))
SHORTLIST_MIN = int(os.environ.get("SCOUT_SHORTLIST_MIN", "65"))
TABLE_MAX = 12


def load_state() -> dict:
    p = HOME / "state.json"
    return json.loads(p.read_text()) if p.exists() else {"seen": {}, "runs": []}


def save_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / "state.json").write_text(json.dumps(state, indent=1, sort_keys=True))


def scan(today: date) -> list[Verdict]:
    events = sources.fetch_devpost()
    print(f"[devpost] {len(events)} open + upcoming online hackathons", flush=True)
    # Cheap pre-filter before fetching rules pages
    candidates = [e for e in events if e.online and e.prize_usd > 0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for ev, text in zip(candidates, pool.map(sources.fetch_rules, candidates)):
            ev.rules_text = text
    print(f"[rules] read {sum(bool(e.rules_text) for e in candidates)} rules pages for eligibility", flush=True)
    verdicts = [evaluate(e, today) for e in events]
    kept = [v for v in verdicts if v.keep]
    print(f"[filter] {len(kept)} pass (online, AU ok, solo, cash), "
          f"{sum(v.score >= SHORTLIST_MIN for v in kept)} score {SHORTLIST_MIN}+", flush=True)
    return verdicts


def render(verdicts: list[Verdict], new_ids: set[str], now: datetime,
           progs: list | None = None, first_run: bool = False) -> tuple[str, str]:
    kept = sorted((v for v in verdicts if v.keep), key=lambda v: -v.score)
    short = [v for v in kept if v.score >= SHORTLIST_MIN]
    new_short = [v for v in short if v.event.id in new_ids]
    skipped = [v for v in verdicts if not v.keep]
    soon = [p for p in (progs or []) if p.deadline and 0 <= (p.deadline - now.date()).days <= 14]
    title = (f"🦃 Scout digest {now:%d %b %Y}: {len(new_short)} new hackathons, "
             f"{len(short)} worth it, {len(soon)} startup deadlines in 2 weeks")
    lines = [
        f"_Scanned {len(verdicts)} online hackathons from Devpost at {now:%H:%M} Perth. "
        f"{len(kept)} passed Tom's filter, {len(short)} scored {SHORTLIST_MIN}+._",
        "",
        "| | Score | Hackathon | Prize | Closes | Signed up |",
        "|---|---|---|---|---|---|",
    ]
    for v in short[:TABLE_MAX]:
        ev = v.event
        mark = "🆕" if ev.id in new_ids else ""
        closes = f"{ev.deadline:%d %b}" if ev.deadline else ev.time_left
        if v.days_left is not None:
            closes += f" ({v.days_left}d)"
        lines.append(f"| {mark} | **{v.score}** | [{ev.title}]({ev.url}) | ${ev.prize_usd:,.0f} | "
                     f"{closes} | {ev.registrations:,} |")
    if len(short) > TABLE_MAX:
        lines.append(f"| | | _+{len(short) - TABLE_MAX} more in the scan file_ | | | |")
    lines += ["", "### What to build"]
    for v in short[:6]:
        ev = v.event
        flags = f" ⚠️ {'; '.join(v.flags)}" if v.flags else ""
        lines += [
            f"**{ev.title}**{flags}",
            f"- Idea: {idea_for(v)}",
            f"- Why {v.score}: {v.reasons[-1]}",
            f"- 👴 Weird Uncle: _{uncle_says(v)}_",
            "",
        ]
    by_reason: dict[str, int] = {}
    for v in skipped:
        key = v.headline_reason.split(" (")[0] or "other"
        by_reason[key] = by_reason.get(key, 0) + 1
    lines += ["<details><summary>Skipped " + str(len(skipped)) + "</summary>", ""]
    lines += [f"- {k}: {n}" for k, n in sorted(by_reason.items(), key=lambda x: -x[1])]
    for v in skipped:
        if "crypto" in v.headline_reason or "hardware" in v.headline_reason:
            lines.append(f"- 👴 on _{v.event.title}_: {uncle_says(v)}")
            break
    lines += ["", "</details>"]
    if progs:
        lines += programs.render_section(progs, now.date(), first_run)
    lines += ["", "---",
              "Ran on a Fly.io Sprite, delivered through the Sprites GitHub connector. "
              "Source: https://github.com/tomcandev/hacksgiving-scout"]
    return title, "\n".join(lines)


def run(dry_run: bool = False) -> int:
    now = datetime.now(PERTH)
    state = load_state()
    verdicts = scan(now.date())
    new_ids = {v.event.id for v in verdicts if v.keep and v.event.id not in state["seen"]}
    pseen = state.setdefault("programs", {})
    progs = programs.scan(now.date(), pseen)
    print(f"[programs] {len(progs)} startup programs re-read, "
          f"{sum(1 for p in progs if p.change and p.change != 'new')} changed", flush=True)
    title, body = render(verdicts, new_ids, now, progs, first_run=not pseen)
    out = HOME / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"digest-{now:%Y%m%d-%H%M}.md").write_text(f"# {title}\n\n{body}\n")
    (out / f"scan-{now:%Y%m%d-%H%M}.json").write_text(json.dumps(
        [dict(v.event.to_json(), keep=v.keep, score=v.score, reasons=v.reasons, flags=v.flags)
         for v in verdicts], indent=1))
    if dry_run:
        print(title + "\n\n" + body)
        return 0
    url = deliver(title, body)
    programs.remember(progs, pseen)
    for v in verdicts:
        if v.keep:
            state["seen"].setdefault(v.event.id, now.isoformat())
    state["runs"].append({"at": now.isoformat(), "scanned": len(verdicts),
                          "new": len(new_ids), "digest": url})
    state["runs"] = state["runs"][-60:]
    save_state(state)
    return 0


def loop() -> None:
    hour = int(os.environ.get("SCOUT_HOUR", "8"))
    while True:
        now = datetime.now(PERTH)
        nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        print(f"[loop] next run {nxt.isoformat()}", flush=True)
        time.sleep((nxt - now).total_seconds())
        try:
            run()
        except Exception as exc:  # keep the service alive; report next time
            print(f"[loop] run failed: {exc}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scout")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true")
    sub.add_parser("loop")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        return run(args.dry_run)
    loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

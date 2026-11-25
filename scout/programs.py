"""Startup competitions, accelerators, grants and awards.

Unlike hackathons there is no API, so the agent keeps a seed list (programs.json),
re-reads each official page every run and watches for change: dates that appear
or move, and 'applications open/closed' wording. The seed deadline drives the
countdown; the page drives the 'something changed, go look' flag.
"""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .sources import MONTHS, html_to_text, http_get

HERE = Path(__file__).parent
DATE_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*,?\s+(20\d\d)\b"
    r"|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)\b",
    re.I)
OPEN_RE = re.compile(r"applications? (?:are |is )?(?:now )?open|apply now|now accepting|nominations? (?:are )?open", re.I)
CLOSED_RE = re.compile(r"applications? (?:are |have |has )?(?:now )?closed|nominations? (?:are |have )?closed|no longer accepting", re.I)


@dataclass
class Program:
    name: str
    url: str
    value: str
    kind: str
    deadline: date | None = None
    month: int | None = None
    rolling: bool = False
    needs: list[str] = field(default_factory=list)
    # filled per run
    page_dates: list[str] = field(default_factory=list)
    page_state: str = "unknown"  # open / closed / unknown / unreachable
    fingerprint: str = ""
    blockers: list[str] = field(default_factory=list)
    change: str = ""  # new / dates changed / opened / closed / ""


def load(today: date) -> list[Program]:
    seed = json.loads((HERE / "programs.json").read_text())["programs"]
    profile = json.loads((HERE / "profile.json").read_text())
    out = []
    for p in seed:
        prog = Program(name=p["name"], url=p["url"], value=p.get("value", ""), kind=p.get("kind", ""),
                       deadline=date.fromisoformat(p["deadline"]) if p.get("deadline") else None,
                       month=p.get("month"), rolling=p.get("rolling", False), needs=p.get("needs", []))
        prog.blockers = [profile["missing"].get(n, n) for n in prog.needs if n not in profile["has"]]
        out.append(prog)
    return out


def _dates_in(text: str, today: date) -> list[str]:
    found = set()
    for m in DATE_RE.finditer(text):
        if m.group(1):
            d, mon, y = int(m.group(1)), m.group(2), int(m.group(3))
        else:
            mon, d, y = m.group(4), int(m.group(5)), int(m.group(6))
        try:
            dt = date(y, MONTHS[mon.lower()[:3]], d)
        except ValueError:
            continue
        if -30 <= (dt - today).days <= 450:
            found.add(dt.isoformat())
    return sorted(found)


def read_page(prog: Program, today: date) -> Program:
    try:
        text = html_to_text(http_get(prog.url))
    except Exception:
        prog.page_state = "unreachable"
        return prog
    prog.page_dates = _dates_in(text, today)
    opened, closed = bool(OPEN_RE.search(text)), bool(CLOSED_RE.search(text))
    prog.page_state = "open" if opened and not closed else "closed" if closed and not opened else "unknown"
    prog.fingerprint = hashlib.sha1(
        (prog.page_state + "|" + ",".join(prog.page_dates)).encode()).hexdigest()[:12]
    return prog


def scan(today: date, seen: dict) -> list[Program]:
    progs = load(today)
    with ThreadPoolExecutor(max_workers=8) as pool:
        progs = list(pool.map(lambda p: read_page(p, today), progs))
    for p in progs:
        before = seen.get(p.url)
        if p.page_state == "unreachable":
            continue
        if before is None:
            p.change = "new"
        elif before.get("fp") != p.fingerprint:
            if before.get("state") != p.page_state and p.page_state in ("open", "closed"):
                p.change = p.page_state
            else:
                added = sorted(set(p.page_dates) - set(before.get("dates", [])))
                p.change = "dates changed" + (f" (+{', '.join(added[:2])})" if added else "")
    return progs


def remember(progs: list[Program], seen: dict) -> None:
    for p in progs:
        if p.page_state != "unreachable":
            seen[p.url] = {"fp": p.fingerprint, "state": p.page_state, "dates": p.page_dates}


def days_left(p: Program, today: date) -> int | None:
    return (p.deadline - today).days if p.deadline else None


def render_section(progs: list[Program], today: date, first_run: bool) -> list[str]:
    upcoming = sorted((p for p in progs if p.deadline and days_left(p, today) >= 0),
                      key=lambda p: p.deadline)
    rolling = [p for p in progs if p.rolling]
    seasonal = sorted((p for p in progs if not p.deadline and not p.rolling and p.month),
                      key=lambda p: (p.month - today.month) % 12)
    flag = {"opened": "🟢 opened", "closed": "🔴 closed"}

    lines = ["", "## Startup competitions, accelerators & grants", "",
             "| Program | Closes | Value | Page | Can enter? |", "|---|---|---|---|---|"]
    for p in upcoming:
        d = days_left(p, today)
        change = "" if first_run else flag.get(p.change, f"🔄 {p.change}" if p.change and p.change != "new" else "")
        page = change or p.page_state
        ok = "✅" if not p.blockers else "⛔ " + "; ".join(p.blockers)
        urgent = " ⏰" if d <= 7 else ""
        lines.append(f"| [{p.name}]({p.url}) | {p.deadline:%d %b} ({d}d){urgent} | {p.value} | {page} | {ok} |")
    lines += ["", "**Always open:** " + " · ".join(
        f"[{p.name}]({p.url})" + (" ⛔" if p.blockers else "") for p in rolling)]
    soon = [p for p in seasonal if (p.month - today.month) % 12 <= 4]
    if soon:
        lines += ["", "**Opening in the next few months:** " + " · ".join(
            f"{date(2000, p.month, 1):%b} [{p.name}]({p.url})" for p in soon)]
    changed = [p for p in progs if p.change and p.change != "new" and not first_run]
    if changed:
        lines += ["", "**Changed since last run:** " + "; ".join(f"{p.name}: {p.change}" for p in changed)]
    unreachable = [p.name for p in progs if p.page_state == "unreachable"]
    if unreachable:
        lines += ["", f"_Could not read: {', '.join(unreachable)}_"]
    return lines

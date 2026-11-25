"""Where hackathons come from. Stdlib only so the Sprite needs no pip install."""
from __future__ import annotations

import html
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime

UA = "Mozilla/5.0 (hacksgiving-scout; +https://github.com/tomcandev/hacksgiving-scout)"
DEVPOST_API = (
    "https://devpost.com/api/hackathons?status[]={status}&challenge_type[]=online"
    "&order_by=prize-amount&page={page}"
)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


@dataclass
class Event:
    id: str
    title: str
    url: str
    source: str
    organizer: str = ""
    online: bool = True
    prize_usd: float = 0.0
    cash_prizes: int = 0
    registrations: int = 0
    themes: list[str] = field(default_factory=list)
    period: str = ""
    deadline: date | None = None
    time_left: str = ""
    status: str = "open"
    rules_text: str = ""

    def to_json(self) -> dict:
        d = self.__dict__.copy()
        d["deadline"] = self.deadline.isoformat() if self.deadline else None
        d.pop("rules_text", None)
        return d


def http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_money(raw: str) -> float:
    text = re.sub(r"<[^>]+>", "", raw or "")
    digits = re.sub(r"[^0-9.]", "", text)
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def parse_period_end(period: str) -> date | None:
    """Devpost periods look like 'Oct 27 - Dec 22, 2026', 'Nov 20 - 23, 2026'
    or 'Nov 01, 2026 - Jan 12, 2027'. We only need the end date."""
    if not period:
        return None
    end = period.split(" - ")[-1].strip()
    years = re.findall(r"(\d{4})", period)
    m = re.match(r"([A-Za-z]{3})\w*\s+(\d{1,2})(?:,\s*(\d{4}))?", end)
    if m:
        mon, day, yr = MONTHS.get(m.group(1).lower()), int(m.group(2)), m.group(3)
    else:
        m = re.match(r"(\d{1,2})(?:,\s*(\d{4}))?", end)
        if not m:
            return None
        start_mon = re.match(r"([A-Za-z]{3})", period)
        mon = MONTHS.get(start_mon.group(1).lower()) if start_mon else None
        day, yr = int(m.group(1)), m.group(2)
    year = int(yr or (years[-1] if years else datetime.utcnow().year))
    try:
        return date(year, mon, day) if mon else None
    except ValueError:
        return None


def html_to_text(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def fetch_devpost(statuses=("open", "upcoming"), max_pages: int = 6) -> list[Event]:
    events: dict[str, Event] = {}
    for status in statuses:
        for page in range(1, max_pages + 1):
            data = json.loads(http_get(DEVPOST_API.format(status=status, page=page)))
            items = data.get("hackathons", [])
            for h in items:
                ev = Event(
                    id=f"devpost:{h['id']}",
                    title=h.get("title", "").strip(),
                    url=h.get("url", ""),
                    source="Devpost",
                    organizer=h.get("organization_name") or "",
                    online=(h.get("displayed_location") or {}).get("location", "").lower() == "online",
                    prize_usd=parse_money(h.get("prize_amount", "")),
                    cash_prizes=(h.get("prizes_counts") or {}).get("cash", 0) or 0,
                    registrations=h.get("registrations_count") or 0,
                    themes=[t["name"] for t in h.get("themes", [])],
                    period=h.get("submission_period_dates", ""),
                    time_left=h.get("time_left_to_submission", "") or "",
                    status=status,
                )
                if h.get("invite_only"):
                    continue
                ev.deadline = parse_period_end(ev.period)
                events.setdefault(ev.id, ev)
            if len(items) < 9:
                break
    return list(events.values())


def fetch_rules(ev: Event) -> str:
    """Grab the rules page so eligibility is read, not guessed."""
    if ev.source != "Devpost" or not ev.url:
        return ""
    try:
        return html_to_text(http_get(ev.url.rstrip("/") + "/rules"))[:120_000]
    except Exception:  # rules page missing or slow: fall back to overview
        try:
            return html_to_text(http_get(ev.url))[:60_000]
        except Exception:
            return ""

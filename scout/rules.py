"""Tom's filter, written down once.

A hackathon is worth his evenings only when all four hold:
1. online, open to someone living in Australia, solo entry allowed
2. real cash prizes
3. the thing you build is an app he could publish (store or web)
4. it fits in 1-2 weeks of evenings
Crypto/token, hardware and in-person-abroad events are skipped outright.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date

from .sources import Event

SKIP_PATTERNS = {
    "crypto/token": r"\b(crypto|blockchain|web3|defi|nft|token(?:s|ized)?|solana|ethereum|bitcoin|onchain|on-chain|stablecoin|dao)\b",
    "hardware": r"\b(hardware|arduino|raspberry pi|fpga|robot(?:ics)?|embedded|iot|microcontroller|drone)\b",
}
APP_THEMES = {
    "Mobile": 10, "Web": 8, "Machine Learning/AI": 6, "Productivity": 6, "Education": 8,
    "Health": 5, "Social Good": 4, "Design": 4, "Lifestyle": 5, "Communication": 4,
    "Gaming": 4, "Music/Art": 3, "Beginner Friendly": 2, "Open Ended": 6,
}
APP_WORDS = r"\b(app|apps|mobile|ios|android|flutter|react native|web app|pwa|firebase|expo|consumer)\b"
NOT_STORE_WORDS = r"\b(plugin|extension|forge|atlassian|salesforce|servicenow|snowflake|databricks|kubernetes|devops|sdk integration|ar lens|lens studio|nas)\b"


@dataclass
class Verdict:
    event: Event
    keep: bool
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    days_left: int | None = None

    @property
    def headline_reason(self) -> str:
        return self.reasons[0] if self.reasons else ""


def _near(text: str, a: str, b: str, window: int = 220) -> bool:
    for m in re.finditer(a, text):
        chunk = text[max(0, m.start() - window): m.end() + window]
        if re.search(b, chunk):
            return True
    return False


def eligibility(rules: str) -> tuple[str, list[str]]:
    """Return ('ok'|'assumed'|'no', notes) for an adult Perth resident entering solo."""
    t = rules.lower()
    notes: list[str] = []
    if not t:
        return "assumed", ["rules page not readable"]
    if _near(t, r"australia", r"(exclud|not eligible|ineligible|void|prohibited|cannot participate)"):
        return "no", ["rules exclude Australia"]
    m = re.search(r"(?:only|solely) (?:open to|available to)?\s*(?:legal )?residents? of ([a-z ,]+)", t) or \
        re.search(r"open (?:only )?to (?:legal )?residents? of (the )?(united states|u\.s\.|usa|canada|india|uk|united kingdom|singapore)[^.]{0,80}", t)
    worldwide = re.search(r"(worldwide|all countries|any country|most countries|global(?:ly)? open)", t)
    if m and "australia" not in m.group(0) and not worldwide:
        return "no", [f"residency limited ({m.group(0)[:60].strip()}...)"]
    if re.search(r"teams? (?:must|need to) (?:have|consist of) (?:at least|a minimum of) (2|two)|minimum (?:team size|of) (2|two)", t):
        return "no", ["no solo entries"]
    if re.search(r"high school|secondary school|ages? 13|under the age of 18 only", t) and not re.search(r"18 years|age of majority", t):
        return "no", ["aimed at teens"]
    if re.search(r"students only|only (?:open to )?(?:current )?(?:university |college )?students|must be (?:a )?(?:currently )?enrolled", t):
        notes.append("students only (Tom ok until end-2026)")
    if "australia" in t or worldwide:
        return "ok", notes
    return "assumed", notes + ["standard terms, Australia not named"]


def evaluate(ev: Event, today: date) -> Verdict:
    blob = " ".join([ev.title, ev.organizer, " ".join(ev.themes)]).lower()
    v = Verdict(event=ev, keep=False)
    if ev.deadline:
        v.days_left = (ev.deadline - today).days

    if not ev.online:
        v.reasons.append("in person")
        return v
    for label, pat in SKIP_PATTERNS.items():
        if re.search(pat, blob):
            v.reasons.append(f"skip: {label}")
            return v
    if ev.prize_usd <= 0 or ev.cash_prizes <= 0:
        v.reasons.append("no cash prize")
        return v
    if v.days_left is not None and v.days_left < 2:
        v.reasons.append("closes in under 2 days")
        return v

    elig, notes = eligibility(ev.rules_text)
    v.flags.extend(notes)
    if elig == "no":
        v.reasons.extend(notes or ["not eligible"])
        return v

    # score out of 100
    # log scale: $1k -> 6, $10k -> 18, $100k -> 30
    prize = max(0, min(30, round(12 * math.log10(max(ev.prize_usd, 1)) - 30)))
    app = sum(APP_THEMES.get(t, 0) for t in ev.themes)
    rules_l = ev.rules_text.lower()
    if re.search(APP_WORDS, blob) or len(re.findall(APP_WORDS, rules_l)) >= 5:
        app += 8
    if re.search(NOT_STORE_WORDS, blob):
        app -= 12
        v.flags.append("output is a plugin/platform add-on, not a store app")
    app = max(0, min(25, app))
    d = v.days_left
    if d is None:
        timing = 10
    elif d <= 6:
        timing = 8
        v.flags.append("tight: under a week")
    elif d <= 30:
        timing = 20
    else:
        timing = 14
    r = ev.registrations
    crowd = 15 if r < 500 else 11 if r < 2000 else 7 if r < 8000 else 3
    sure = 10 if elig == "ok" else 6
    v.score = prize + app + timing + crowd + sure
    v.keep = True
    v.reasons.append(f"prize {prize}/30, app-fit {app}/25, timing {timing}/20, crowd {crowd}/15, eligibility {sure}/10")
    return v

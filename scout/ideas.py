"""One concrete project idea per shortlisted event, and the Weird Uncle's opinion.

Ideas lean on things Tom already ships (PTE Flow, Colloca, HumaWrite, Flowthrough)
so a hackathon entry can become a real app afterwards.
"""
from __future__ import annotations

import hashlib
import re

from .rules import Verdict

IDEA_TABLE = [
    (r"\b(game|gaming|puzzle|reddit|devvit)\b", "Word Duel: a daily head-to-head collocation puzzle from Colloca's data, playable on web and mobile"),
    (r"\b(education|edtech|language|students?|accessib\w*|learning platform)\b", "Colloca Daily: a 2-minute collocation drill each morning with streaks and a share card, shipped to both stores"),
    (r"\b(health|wellness|fitness|mental|safe\w*)\b", "Calm Speaking: an anxiety-friendly PTE speaking warm-up that coaches breathing before each recording"),
    (r"\b(design|art|drawing|pixels?|fashion|creative)\b", "Prompt Postcard: turn a photo into a themed greeting card in one tap, export as a share image"),
    (r"\b(productivity|enterprise|developer|devtools?|founders?|startup|msp)\b", "Flowthrough Lite: paste a PR link, get a guided 5-step review walkthrough on your phone"),
    (r"\b(writing|content|social|creator|communication)\b", "HumaWrite Pocket: rewrite a draft in your own voice before posting, with a tone slider"),
    (r"\b(voice|speech|audio|music)\b", "Accent Mirror: record one sentence, hear it back with stress and pauses marked, PTE-style"),
    (r"\b(agents?|agentic|kiro|llm|ai|machine learning)\b", "PTE Coach agent: grade a Read Aloud answer on-device, then plan tomorrow's practice in the cloud"),
]
DEFAULT_IDEA = "Tiny Tutor: one screen, one skill per day, store-ready by the deadline"

UNCLE = {
    "big": [
        "Back in my day the prize was a slice of pumpkin pie. {prize}? Pass the gravy, kid's going pro.",
        "{prize} for a weekend of typing? I sold my first app for a firm handshake.",
    ],
    "crowd": [
        "{n} people signed up. I've seen smaller crowds at a Black Friday TV aisle.",
    ],
    "tight": [
        "Closes in {d} days. That's less time than this turkey spent thawing.",
    ],
    "crypto": [
        "A token? In my day a token got you on the bus. Skipped.",
    ],
    "hardware": [
        "Hardware? The only thing I solder is leftovers onto a sandwich. Skipped.",
    ],
    "default": [
        "Mark my words, this one's got legs. Probably.",
        "Your aunt thinks you should do this one. Your aunt also thinks the cloud is weather.",
    ],
}


def _pick(options: list[str], key: str) -> str:
    h = int(hashlib.sha1(key.encode()).hexdigest(), 16)
    return options[h % len(options)]


def idea_for(v: Verdict) -> str:
    blob = " ".join([v.event.title, " ".join(v.event.themes), v.event.organizer]).lower()
    for pat, idea in IDEA_TABLE:
        if re.search(pat, blob):
            sponsor = v.event.organizer.strip()
            return f"{idea} (built on {sponsor}'s stack)" if sponsor else idea
    return DEFAULT_IDEA


def uncle_says(v: Verdict) -> str:
    ev = v.event
    reason = v.headline_reason
    if "crypto" in reason:
        return _pick(UNCLE["crypto"], ev.id)
    if "hardware" in reason:
        return _pick(UNCLE["hardware"], ev.id)
    if ev.prize_usd >= 20_000:
        return _pick(UNCLE["big"], ev.id).format(prize=f"${ev.prize_usd:,.0f}")
    if v.days_left is not None and v.days_left <= 6:
        return _pick(UNCLE["tight"], ev.id).format(d=v.days_left)
    if ev.registrations >= 5000:
        return _pick(UNCLE["crowd"], ev.id).format(n=f"{ev.registrations:,}")
    return _pick(UNCLE["default"], ev.id)

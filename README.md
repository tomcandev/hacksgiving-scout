# hacksgiving-scout 🦃

A personal agent that lives on a [Fly.io Sprite](https://fly.io/sprites). Each morning it reads every open online hackathon on Devpost and re-checks a list of startup competitions, accelerators, grants and awards, keeps only what a solo indie dev in Perth can actually enter and win, and drops one digest into GitHub through the Sprites GitHub connector. A Weird Uncle comments on each pick.

Built for [Fly.io Hacksgiving 2026](https://fly.io/hacksgiving/) (23–29 Nov 2026).

## Plan (written before the code)

1. Source: Devpost's public hackathon API (open + upcoming, online only), sorted by prize.
2. For every candidate with a cash prize, fetch its rules page and read eligibility instead of guessing.
3. Hard filter: online, open to Australian residents, solo allowed, real cash, not for teens.
4. Skip outright: crypto/token, hardware, in-person.
5. Score out of 100: prize (30), app-fit (25: will the output be a publishable app?), timing (20), crowd size (15), eligibility certainty (10).
6. Remember what was seen in `~/.scout/state.json` on the Sprite's persistent disk, so the digest flags 🆕 events.
7. One concrete project idea per shortlisted event, reusing apps the owner already ships.
8. Deliver through a Sprites connector: the gateway holds the GitHub credential, the agent never sees a token.
9. Run daily at 08:00 Perth as a Sprite service; each run opens a new digest issue and closes the previous one.
10. Keep it stdlib-only Python so the Sprite needs no install step.

Added mid-week: startup competitions, accelerators and grants. There is no API for those, so the agent keeps a seed list of official pages (`scout/programs.json`), re-reads each page every run, flags dates that move and applications that open or close, counts down deadlines, and marks programs blocked by a missing requirement (ABN, company, full-time) from `scout/profile.json`.

## How it works

```
┌─────────── Fly.io Sprite: hacksgiving-scout ───────────┐
│  sprite-env service "scout" → python3 -m scout.main loop│
│    ├─ sources.py  Devpost API + each event's /rules     │
│    ├─ rules.py    filter + score (Tom's criteria)       │
│    ├─ programs.py startup programs: page diff + deadlines│
│    ├─ ideas.py    project idea + Weird Uncle one-liner  │
│    └─ deliver.py  POST api.sprites.dev/v1/gateway/      │
│                   github/<conn>/repos/…/issues          │
└──────────────────────────────┬──────────────────────────┘
                               ▼
               GitHub issue "🦃 Hackathon digest …" → phone notification
```

## Run it

```bash
# on your machine
curl -fsSL https://sprites.dev/install.sh | sh
sprite login
sprite create hacksgiving-scout
./deploy/deploy.sh            # pushes code, starts the daily service

# one pass by hand
sprite exec -s hacksgiving-scout --dir /home/sprite/hacksgiving-scout -- python3 -m scout.main run
sprite exec -s hacksgiving-scout --dir /home/sprite/hacksgiving-scout -- python3 -m scout.main run --dry-run
```

Connect GitHub once in the Fly.io dashboard (Sprites → Connectors → GitHub) or with `sprite api "/v1/oauth/github/authorize?scopes=public_repo"`. The agent finds the connection by itself through `https://api.sprites.dev/v1/gateway/list`.

Settings (env vars): `SCOUT_REPO` (where digests go, default `tomcandev/hacksgiving-scout`), `SCOUT_HOUR` (Perth hour, default 8), `SCOUT_SHORTLIST_MIN` (default 65).

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

## Licence

MIT

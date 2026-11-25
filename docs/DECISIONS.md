# Decisions

Calls made on the way, newest last. Dates are Perth time.

- **2026-11-25 New code only.** Hacksgiving requires the project to be built during the week, so this repo is written from scratch. The earlier hackathon-scout skill was read for criteria only; no code copied.
- **2026-11-25 Python stdlib only.** Sprites ship Python 3.13; no pip step means a deploy is just `git clone`.
- **2026-11-25 Devpost as the one source.** Its public API returns open and upcoming online events with prize, themes and dates. Instead of adding thin second sources, the agent reads each event's `/rules` page, which is what actually decides eligibility for an Australian resident. lablab.ai and Luma can be added later as `fetch_*` functions.
- **2026-11-25 GitHub connector for delivery.** Of the Sprites connectors, GitHub is first-party, free, needs only an OAuth click, and the GitHub mobile app turns each digest issue into a phone notification. The agent finds the connection through `gateway/list`, so no IDs or tokens live in the repo. Each run opens a new issue and closes the previous one.
- **2026-11-25 Rule-based ideas, no LLM key.** An LLM connector (Anthropic/OpenAI) would bill a separate account. Ideas come from a theme table that maps to apps Tom already ships; good enough for a digest and costs nothing.
- **2026-11-25 Weird Uncle voice.** A one-liner per pick, deterministic per event. Cheap, makes the digest fun to read, and aims at the Weird Uncle Award.
- **2026-11-25 Scheduling as a Sprite service.** `sprite-env services create scout … loop` sleeps until 08:00 Perth, then runs. Services restart on boot. A sleeping Python process uses almost no CPU, so it stays inside the Free plan.
- **2026-11-25 Scores.** prize 30 (log scale: $1k→6, $10k→18, $100k→30), app-fit 25, timing 20, crowd 15, eligibility certainty 10. Shortlist at 65+. Events closing in under 2 days are dropped.
- **2026-11-25 Public identity.** Repo under `tomcandev`, licence "Tom (tomcan.dev)", per Tom's preference for the alias.
- **2026-11-25 Startup programs in the same digest.** Tom asked for startup competitions too. No public API covers them, so a seed list of official pages plus page-change detection (dates found on the page, open/closed wording) is the cheapest honest signal. Only public facts go in the repo; personal notes (visa, plans) stay in Tom's private tracker. No aggregator added yet, to keep the 1–2 day scope; one can slot in as another source later.
- **2026-11-26 Connector policy.** The GitHub connection only serves Sprites whose name starts with `hacksgiving-scout`, and only `/repos/tomcandev/hacksgiving-scout/*`. (API field is `name_prefix`; `sprite_name_prefix` is accepted but ignored.)
- **2026-11-26 Demo built from real artefacts.** `tools/make_demo.py` renders the real run transcript and screenshots of the real digest issue into an mp4, instead of a desktop screen recording that would show unrelated windows.

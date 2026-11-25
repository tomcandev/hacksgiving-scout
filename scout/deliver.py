"""Send the digest through a Sprites connector.

Inside a Sprite, the Fly.io gateway at api.sprites.dev holds the credential, so this
code never sees a GitHub token: it calls
https://api.sprites.dev/v1/gateway/<provider>/<connection_id>/<path>
and the gateway attaches auth. Outside a Sprite we just print.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

GATEWAY = os.environ.get("SPRITES_GATEWAY", "https://api.sprites.dev/v1/gateway")


def _call(method: str, url: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "User-Agent": "hacksgiving-scout",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode() or "{}"
        return json.loads(raw)


def find_connection(provider: str) -> str | None:
    explicit = os.environ.get(f"SCOUT_{provider.upper()}_CONNECTION")
    if explicit:
        return explicit
    try:
        listing = _call("GET", f"{GATEWAY}/list")
    except (urllib.error.URLError, ValueError):
        return None
    for conn in listing.get("connections", []) if isinstance(listing, dict) else []:
        if conn.get("provider") == provider:
            return conn.get("id") or conn.get("connection_id")
    return None


class GitHubIssues:
    """Digest = one GitHub issue per run; the previous digest gets closed."""

    label = "scout-digest"

    def __init__(self, repo: str, connection: str):
        self.repo = repo
        self.base = f"{GATEWAY}/github/{connection}"

    def _gh(self, method: str, path: str, body: dict | None = None):
        return _call(method, f"{self.base}{path}", body)

    def send(self, title: str, body: str) -> str:
        try:
            self._gh("POST", f"/repos/{self.repo}/labels",
                     {"name": self.label, "color": "d97706", "description": "Daily hackathon digest"})
        except urllib.error.HTTPError:
            pass  # label exists already
        old = self._gh("GET", f"/repos/{self.repo}/issues?labels={self.label}&state=open&per_page=20")
        issue = self._gh("POST", f"/repos/{self.repo}/issues",
                         {"title": title, "body": body, "labels": [self.label]})
        for prev in old if isinstance(old, list) else []:
            self._gh("PATCH", f"/repos/{self.repo}/issues/{prev['number']}",
                     {"state": "closed", "state_reason": "completed"})
        return issue.get("html_url", "")


def deliver(title: str, body: str) -> str:
    repo = os.environ.get("SCOUT_REPO", "tomcandev/hacksgiving-scout")
    conn = find_connection("github")
    if not conn:
        print("[deliver] no GitHub connector visible from here; printing digest instead\n")
        print(title + "\n\n" + body)
        return ""
    url = GitHubIssues(repo, conn).send(title, body)
    print(f"[deliver] digest posted via Sprites GitHub connector: {url}")
    return url

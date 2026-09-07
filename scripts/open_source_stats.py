#!/usr/bin/env python3
"""Render the Open Source Stats card as themed SVGs into assets/.

The sponsor figure is all-time: sponsorshipsAsMaintainer with activeOnly=false
so lapsed sponsors still count, unlike the `sponsors` field which only counts
currently active ones.

Queries the GitHub GraphQL API for the totals shown on the card and writes a
dark and a light variant using the README's locked palette. Committed to the
repo by .github/workflows/stats.yml so the README can reference them by
relative path.
"""
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "emrementese")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

QUERY = """
{
  user(login: "%s") {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes { stargazerCount forkCount watchers { totalCount } }
    }
    sponsorshipsAsMaintainer(first: 100, activeOnly: false) { totalCount }
    followers { totalCount }
  }
}
""" % USER

# GitHub Octicons (16px), used under the MIT licence.
ICONS = {
    "heart": "m8 14.25.345.666a.75.75 0 0 1-.69 0l-.008-.004-.018-.01a7.152 7.152 0 0 1-.31-.17 22.055 22.055 0 0 1-3.434-2.414C2.045 10.731 0 8.35 0 5.5 0 2.836 2.086 1 4.25 1 5.797 1 7.153 1.802 8 3.02 8.847 1.802 10.203 1 11.75 1 13.914 1 16 2.836 16 5.5c0 2.85-2.045 5.231-3.885 6.818a22.066 22.066 0 0 1-3.744 2.584l-.018.01-.006.003h-.002Z",
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "fork": "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z",
    "people": "M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Z",
    "eye": "M8 2c1.981 0 3.671.992 4.933 2.078 1.27 1.091 2.187 2.345 2.637 3.023a1.62 1.62 0 0 1 0 1.798c-.45.678-1.367 1.932-2.637 3.023C11.67 13.008 9.981 14 8 14c-1.981 0-3.671-.992-4.933-2.078C1.797 10.83.88 9.576.43 8.898a1.62 1.62 0 0 1 0-1.798c.45-.677 1.367-1.931 2.637-3.022C4.33 2.992 6.019 2 8 2ZM1.679 7.932a.12.12 0 0 0 0 .136c.411.622 1.241 1.75 2.366 2.717C5.176 11.758 6.527 12.5 8 12.5c1.473 0 2.825-.742 3.955-1.715 1.124-.967 1.954-2.096 2.366-2.717a.12.12 0 0 0 0-.136c-.412-.621-1.242-1.75-2.366-2.717C10.824 4.242 9.473 3.5 8 3.5c-1.473 0-2.825.742-3.955 1.715-1.124.967-1.954 2.096-2.366 2.717ZM8 10a2 2 0 1 1-.001-3.999A2 2 0 0 1 8 10Z",
}

THEMES = {
    "dark":  dict(bg="#0d1117", border="#30363d", text="#c9d1d9", muted="#8b949e", accent="#1F6FEB"),
    "light": dict(bg="#ffffff", border="#d0d7de", text="#1f2328", muted="#59636e", accent="#0969DA"),
}

W, H, PAD = 460, 152, 24
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    user = payload["data"]["user"]
    nodes = user["repositories"]["nodes"]
    return [
        ("people", user["followers"]["totalCount"], "Followers"),
        ("heart", user["sponsorshipsAsMaintainer"]["totalCount"], "Sponsors"),
        ("star", sum(n["stargazerCount"] for n in nodes), "Stargazers"),
        ("fork", sum(n["forkCount"] for n in nodes), "Forkers"),
        ("eye", sum(n["watchers"]["totalCount"] for n in nodes), "Watchers"),
    ]


def render(stats, t):
    cell = (W - PAD * 2) / len(stats)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="Open source statistics">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text x="{PAD}" y="36" font-family="{FONT}" font-size="15" font-weight="600" '
        f'fill="{t["accent"]}">Open Source Stats</text>',
        f'<line x1="{PAD}" y1="52" x2="{W-PAD}" y2="52" stroke="{t["border"]}"/>',
    ]
    for i, (icon, value, label) in enumerate(stats):
        cx = PAD + cell * i + cell / 2
        out.append(
            f'<g transform="translate({cx-8:.1f} 72)"><path d="{ICONS[icon]}" fill="{t["accent"]}"/></g>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="115" font-family="{FONT}" font-size="23" font-weight="700" '
            f'text-anchor="middle" fill="{t["text"]}">{value}</text>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="134" font-family="{FONT}" font-size="11.5" '
            f'text-anchor="middle" fill="{t["muted"]}">{label}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GH_TOKEN or GITHUB_TOKEN is required")
    data = fetch()
    os.makedirs("assets", exist_ok=True)
    for name, theme in THEMES.items():
        path = f"assets/open-source-{name}.svg"
        with open(path, "w") as fh:
            fh.write(render(data, theme))
        print(f"wrote {path}")
    print("  " + ", ".join(f"{l}={v}" for _, v, l in data))

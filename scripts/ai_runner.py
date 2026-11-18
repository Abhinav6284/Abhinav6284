"""Generate an animated SVG: an AI helper runs across the contribution graph
scanning each column, and a developer follows with a wrench "fixing" it.

Usage: python scripts/ai_runner.py <github_login> <out_dir>
Needs env GITHUB_TOKEN (the default Actions token works). Falls back to a demo
grid if the API call fails, so the image never breaks.
"""
import json
import os
import sys
import urllib.request

CELL, GAP = 11, 3
STEP = CELL + GAP
LEFT, TOP = 20, 20
DUR = 22.0  # seconds per loop

THEMES = {
    "light": dict(bg="#ffffff", empty="#ebedf0", levels=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
                  scan="#36BCF7", text="#57606a", track="#d0d7de"),
    "dark": dict(bg="#0d1117", empty="#161b22", levels=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
                 scan="#36BCF7", text="#8b949e", track="#30363d"),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch_weeks(login):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("no token")
    q = {"query": "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionLevel}}}}}}",
         "variables": {"l": login}}
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps(q).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[LEVEL.get(d["contributionLevel"], 0) for d in w["contributionDays"]] for w in weeks]


def demo_weeks():
    # Blank grid fallback: never shows contributions that didn't happen.
    return [[0] * 7 for _ in range(53)]


def robot(color):
    # Original AI-helper sprite (not any company's logo): rounded body, visor, antenna.
    return f'''
    <g>
      <line x1="0" y1="-30" x2="0" y2="-37" stroke="{color}" stroke-width="2"/>
      <circle cx="0" cy="-39" r="3" fill="{color}">
        <animate attributeName="opacity" values="1;0.3;1" dur="0.8s" repeatCount="indefinite"/>
      </circle>
      <rect x="-11" y="-30" width="22" height="18" rx="6" fill="{color}"/>
      <rect x="-8" y="-26" width="16" height="8" rx="3" fill="#0d1117"/>
      <circle cx="-3.5" cy="-22" r="1.8" fill="{color}"><animate attributeName="r" values="1.8;0.4;1.8" dur="2.4s" repeatCount="indefinite"/></circle>
      <circle cx="3.5" cy="-22" r="1.8" fill="{color}"><animate attributeName="r" values="1.8;0.4;1.8" dur="2.4s" repeatCount="indefinite"/></circle>
      <rect x="-9" y="-12" width="18" height="10" rx="3" fill="{color}" opacity="0.85"/>
      <line x1="-5" y1="-2" x2="-7" y2="6" stroke="{color}" stroke-width="3" stroke-linecap="round">
        <animate attributeName="x2" values="-7;-2;-7" dur="0.35s" repeatCount="indefinite"/></line>
      <line x1="5" y1="-2" x2="7" y2="6" stroke="{color}" stroke-width="3" stroke-linecap="round">
        <animate attributeName="x2" values="2;7;2" dur="0.35s" repeatCount="indefinite"/></line>
      <text x="0" y="-46" text-anchor="middle" font-family="Fira Code,monospace" font-size="8" fill="{color}">AI</text>
    </g>'''


def developer(skin, shirt, tool):
    return f'''
    <g>
      <circle cx="0" cy="-32" r="6" fill="{skin}"/>
      <path d="M-6,-34 Q0,-42 6,-34 Z" fill="#2d2d2d"/>
      <rect x="-6" y="-25" width="12" height="15" rx="3" fill="{shirt}"/>
      <g>
        <animateTransform attributeName="transform" type="rotate" values="-35 5 -22;25 5 -22;-35 5 -22" dur="0.5s" repeatCount="indefinite"/>
        <line x1="5" y1="-22" x2="14" y2="-27" stroke="{skin}" stroke-width="3" stroke-linecap="round"/>
        <path d="M13,-30 l4,-2 l2,3 l-3,3 Z" fill="{tool}"/>
      </g>
      <line x1="-3" y1="-10" x2="-5" y2="0" stroke="#3b5bdb" stroke-width="3" stroke-linecap="round">
        <animate attributeName="x2" values="-6;-1;-6" dur="0.4s" repeatCount="indefinite"/></line>
      <line x1="3" y1="-10" x2="5" y2="0" stroke="#3b5bdb" stroke-width="3" stroke-linecap="round">
        <animate attributeName="x2" values="1;6;1" dur="0.4s" repeatCount="indefinite"/></line>
      <text x="0" y="-44" text-anchor="middle" font-family="Fira Code,monospace" font-size="8" fill="{shirt}">me</text>
    </g>'''


def build(weeks, theme):
    t = THEMES[theme]
    cols = len(weeks)
    grid_w = cols * STEP
    width = LEFT * 2 + grid_w
    track_y = TOP + 7 * STEP + 52
    height = track_y + 22
    lag = 0.07  # developer trails the AI by 7% of the loop
    run = 0.78  # fraction of the loop spent crossing

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           f'<rect width="100%" height="100%" fill="{t["bg"]}" rx="8"/>']
    for c, week in enumerate(weeks):
        x = LEFT + c * STEP
        frac = c / max(cols - 1, 1)
        ta = round(frac * run, 4)
        tb = round(ta + lag, 4)
        for r, lvl in enumerate(week):
            y = TOP + r * STEP
            final = t["levels"][lvl]
            fixed = final
            kt = [0, ta, min(ta + 0.005, tb), tb, min(tb + 0.005, 0.97), 0.97, 1]
            kt = [round(k, 4) for k in kt]
            vals = [t["empty"], t["empty"], t["scan"], t["scan"], fixed, fixed, t["empty"]]
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{t["empty"]}">'
                       f'<animate attributeName="fill" values="{";".join(vals)}" keyTimes="{";".join(map(str, kt))}" '
                       f'dur="{DUR}s" repeatCount="indefinite"/></rect>')
    out.append(f'<line x1="{LEFT}" y1="{track_y}" x2="{LEFT + grid_w}" y2="{track_y}" stroke="{t["track"]}" stroke-dasharray="4 4"/>')

    x0, x1 = LEFT + CELL / 2, LEFT + (cols - 1) * STEP + CELL / 2

    def mover(sprite, start):
        kt = [0, start, min(start + run, 0.97), 1]
        kt = [round(k, 4) for k in kt]
        xs = [x0 - 30, x0, x1, x1 + 40]
        vals = ";".join(f"{x},{track_y}" for x in xs)
        return (f'<g><animateTransform attributeName="transform" type="translate" values="{vals}" '
                f'keyTimes="{";".join(map(str, kt))}" dur="{DUR}s" repeatCount="indefinite"/>{sprite}</g>')

    out.append(mover(developer("#f1c27d", "#36BCF7" if theme == "dark" else "#0969da", "#bfbfbf"), lag))
    out.append(mover(robot(t["scan"]), 0.0))
    out.append(f'<text x="{LEFT}" y="{height - 6}" font-family="Fira Code,monospace" font-size="9" fill="{t["text"]}">'
               f'AI scans · I fix · ship 🚀</text>')
    out.append('</svg>')
    return "\n".join(out)


def main():
    login = sys.argv[1] if len(sys.argv) > 1 else "Abhinav6284"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "dist"
    try:
        weeks = fetch_weeks(login)
    except Exception as e:  # never fail the workflow
        print("falling back to demo grid:", e)
        weeks = demo_weeks()
    os.makedirs(out_dir, exist_ok=True)
    for theme in ("light", "dark"):
        name = "ai-runner.svg" if theme == "light" else "ai-runner-dark.svg"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(build(weeks, theme))
    print("wrote", out_dir)


if __name__ == "__main__":
    main()

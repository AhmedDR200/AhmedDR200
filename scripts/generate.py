"""Generate terminal-style GitHub stats SVGs from your real contribution data.

Usage:
  GITHUB_TOKEN=... python scripts/generate.py AhmedDR200
  python scripts/generate.py AhmedDR200 --demo     # fake data, for previewing
Outputs: assets/contributions.svg, assets/stats.svg
"""
import json, os, random, sys, urllib.request
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "")
DEMO = "--demo" in sys.argv
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED = "#c9d1d9", "#8b949e"
GREENS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

QUERY = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}"""


def fetch_days():
    if DEMO:
        random.seed(7)
        d0 = date.today() - timedelta(days=364)
        out = OrderedDict()
        for i in range(365):
            d = d0 + timedelta(days=i)
            r = random.random()
            out[d.isoformat()] = 0 if r < 0.12 else int(random.expovariate(1 / 18))
        return out
    token = os.environ["GITHUB_TOKEN"]
    now = datetime.now(timezone.utc)
    body = json.dumps({"query": QUERY, "variables": {
        "login": USER,
        "from": (now - timedelta(days=364)).strftime("%Y-%m-%dT00:00:00Z"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body,
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return OrderedDict((d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"])


def level(n, mx):
    if n <= 0: return 0
    q = n / mx
    return 1 if q < .25 else 2 if q < .5 else 3 if q < .75 else 4


def streaks(days):
    items = [(date.fromisoformat(k), v) for k, v in days.items()]
    best = (0, None, None); cur = 0; start = None
    for d, v in items:
        if v > 0:
            if cur == 0: start = d
            cur += 1
            if cur > best[0]: best = (cur, start, d)
        else:
            cur = 0
    # current streak: walk back from today (today may still be empty)
    cs = 0; cend = None
    rev = items[::-1]
    i = 0
    if rev and rev[0][1] == 0: i = 1
    cstart = None
    while i < len(rev) and rev[i][1] > 0:
        cs += 1; cstart = rev[i][0]; cend = cend or rev[i][0]; i += 1
    return (cs, cstart, cend), best


def fmt(d): return d.strftime("%b %-d") if d else "-"


def svg_head(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}"><rect width="{w}" height="{h}" rx="8" fill="{BG}"/>')


def heatmap(days):
    vals = list(days.items())
    mx = max(v for _, v in vals) or 1
    cell, gap, left, top = 11, 3, 34, 30
    first = date.fromisoformat(vals[0][0])
    offset = (first.weekday() + 1) % 7            # Sunday = 0
    weeks = (len(vals) + offset + 6) // 7
    w = left + weeks * (cell + gap) + 20
    h = top + 7 * (cell + gap) + 52
    s = [svg_head(w, h)]
    last_m = None
    for i, (k, v) in enumerate(vals):
        d = date.fromisoformat(k)
        idx = i + offset
        x = left + (idx // 7) * (cell + gap)
        y = top + (idx % 7) * (cell + gap)
        if d.month != last_m and idx % 7 < 3 or (i == 0):
            if d.month != last_m:
                s.append(f'<text x="{x}" y="{top-10}" font-size="10" fill="{MUTED}">{d.strftime("%b")}</text>')
                last_m = d.month
        s.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{GREENS[level(v, mx)]}"/>')
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.append(f'<text x="8" y="{top + r*(cell+gap) + 9}" font-size="10" fill="{MUTED}">{name}</text>')
    total = sum(v for _, v in vals)
    ly = top + 7 * (cell + gap) + 22
    s.append(f'<text x="{left}" y="{ly}" font-size="11" fill="{TEXT}">{total:,} contributions in the last year</text>')
    lx = w - 20 - 5 * (cell + 3) - 60
    s.append(f'<text x="{lx}" y="{ly}" font-size="10" fill="{MUTED}">Less</text>')
    for i, c in enumerate(GREENS):
        s.append(f'<rect x="{lx + 30 + i*(cell+3)}" y="{ly-10}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    s.append(f'<text x="{lx + 34 + 5*(cell+3)}" y="{ly}" font-size="10" fill="{MUTED}">More</text>')
    s.append("</svg>")
    return "\n".join(s)


def stats_card(days):
    vals = list(days.items())
    total = sum(v for _, v in vals)
    active = sum(1 for _, v in vals if v > 0)
    best_d, best_v = max(vals, key=lambda kv: kv[1])
    cur, lng = streaks(days)
    avg = total / active if active else 0
    months = OrderedDict()
    for k, v in vals:
        m = date.fromisoformat(k).strftime("%Y-%m")
        months[m] = months.get(m, 0) + v

    W, H = 640, 330
    s = [svg_head(W, H)]
    cards = [
        ("current streak", f"{cur[0]} days", f"{fmt(cur[1])} - {fmt(cur[2])}" if cur[0] else "start one today"),
        ("longest streak", f"{lng[0]} days", f"{fmt(lng[1])} - {fmt(lng[2])}"),
        ("contributions", f"{total:,}", "in the last year"),
        ("active days", f"{active}", f"/ {len(vals)}  ({round(100*active/len(vals))}% of the year)"),
        ("best day", f"{best_v}", fmt(date.fromisoformat(best_d))),
        ("avg / active day", f"{avg:.1f}", "contributions"),
    ]
    cw, chh, gx, gy = 196, 62, 10, 10
    for i, (lab, val, sub) in enumerate(cards):
        x = 14 + (i % 3) * (cw + gx)
        y = 14 + (i // 3) * (chh + gy)
        s.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{chh}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>')
        s.append(f'<text x="{x+10}" y="{y+16}" font-size="10" fill="{MUTED}">$ {lab}</text>')
        s.append(f'<text x="{x+10}" y="{y+40}" font-size="22" font-weight="700" fill="#39d353">{val}</text>')
        s.append(f'<text x="{x+10}" y="{y+55}" font-size="9" fill="{MUTED}">{sub}</text>')

    # monthly bars
    by = 168
    s.append(f'<rect x="14" y="{by}" width="{W-28}" height="{H-by-14}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>')
    s.append(f'<text x="24" y="{by+18}" font-size="10" fill="{MUTED}">$ contributions / month</text>')
    mx = max(months.values()) or 1
    n = len(months)
    bw = (W - 28 - 40) / n
    base, ph = H - 36, 90
    for i, (m, v) in enumerate(months.items()):
        hh = max(2, ph * v / mx) if v else 2
        x = 34 + i * bw
        s.append(f'<rect x="{x:.1f}" y="{base-hh:.1f}" width="{bw-8:.1f}" height="{hh:.1f}" rx="2" fill="#39d353" opacity="{0.45 + 0.55*v/mx:.2f}"/>')
        lbl = date.fromisoformat(m + "-01").strftime("%b")[0]
        s.append(f'<text x="{x + (bw-8)/2:.1f}" y="{base+13}" font-size="9" text-anchor="middle" fill="{MUTED}">{lbl}</text>')
        if v == mx:
            s.append(f'<text x="{x + (bw-8)/2:.1f}" y="{base-hh-5:.1f}" font-size="9" text-anchor="middle" fill="{TEXT}">{v:,}</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    days = fetch_days()
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "contributions.svg"), "w").write(heatmap(days))
    open(os.path.join(OUT, "stats.svg"), "w").write(stats_card(days))
    print("ok", len(days), "days")

"""Render the animated, terminal-style SVGs used by the profile README.

Usage:
  GITHUB_TOKEN=... python scripts/generate.py AhmedDR200
  python scripts/generate.py AhmedDR200 --demo     # fake data, for previewing
Outputs (assets/): hero.svg, portrait.svg, contributions.svg, stats.svg, stack.svg

Edit the PROFILE block to change the text. portrait.svg is built from
assets/portrait.txt, which scripts/make_ascii.py writes next to portrait.png.
"""
import json, os, random, sys, urllib.request
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "")
DEMO = "--demo" in sys.argv
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

# ---- PROFILE ---------------------------------------------------------------
HOST = "ahmed@github"
NAME = "Ahmed Magdy"
ROLE = "Backend Engineer · Node.js · NestJS · Express.js"
FOCUS = "Scalable APIs, microservices and cloud-based systems."
STACK = [
    ("languages", ["TypeScript", "JavaScript", "Python"]),
    ("backend", ["Node.js", "NestJS", "Express.js"]),
    ("databases", ["PostgreSQL", "MongoDB", "SQLite"]),
    ("orm", ["Prisma", "Sequelize"]),
    ("devops", ["Docker", "Git", "Render", "Vercel"]),
    ("tooling", ["Postman", "ESLint"]),
]

# ---- THEME -----------------------------------------------------------------
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED, BRIGHT = "#c9d1d9", "#8b949e", "#e6edf3"
GREEN, BLUE, KEY, STR = "#39d353", "#79c0ff", "#7ee787", "#a5d6ff"
GREENS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
CW = 0.6  # monospace advance in em; typed runs are pinned to it with textLength
BAR = 35  # title bar height

CSS = """
text{font-family:%s}
.fade{animation:fade .5s ease-out both}
.rise{animation:rise .6s cubic-bezier(.2,.7,.2,1) both}
.on{opacity:0;animation:on linear}
.blink{opacity:0;animation:blink 1.1s steps(1) infinite}
.pulse{animation:pulse 2s ease-in-out infinite}
@keyframes fade{from{opacity:0}}
@keyframes rise{from{opacity:0;transform:translateY(8px)}}
@keyframes on{from,to{opacity:1}}
@keyframes blink{0%%{opacity:1}50%%{opacity:0}}
@keyframes pulse{50%%{opacity:.25}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.cover{display:none}}
""" % FONT

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


# ---- WINDOW CHROME ---------------------------------------------------------

def window(w, h, title, body, css="", defs="", status=""):
    """A macOS-style terminal window; body is clipped to the area under the title bar."""
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">',
         f'<style>{CSS}{css}</style>',
         f'<defs><clipPath id="body"><rect x="1" y="{BAR}" width="{w-2:.0f}" height="{h-BAR-1:.0f}" rx="9"/></clipPath>{defs}</defs>',
         f'<rect width="{w:.0f}" height="{h:.0f}" rx="10" fill="{BG}"/>',
         f'<path d="M.5 {BAR}.5V10.5a10 10 0 0 1 10-10h{w-21:.0f}a10 10 0 0 1 10 10v{BAR}z" fill="{PANEL}"/>',
         f'<line x1=".5" y1="{BAR}.5" x2="{w-.5:.1f}" y2="{BAR}.5" stroke="{BORDER}"/>']
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        s.append(f'<circle cx="{20 + i*20}" cy="17.5" r="6" fill="{c}"/>')
    s.append(f'<text x="{w/2:.1f}" y="22" font-size="12" fill="{MUTED}" text-anchor="middle">{escape(title)}</text>')
    if status:
        s.append(f'<circle class="pulse" cx="{w-20-len(status)*6.6:.1f}" cy="17.5" r="3.5" fill="{GREEN}"/>')
        s.append(f'<text x="{w-14:.1f}" y="21.5" font-size="11" fill="{MUTED}" text-anchor="end">{escape(status)}</text>')
    s.append(f'<g clip-path="url(#body)">{"".join(body)}</g>')
    s.append(f'<rect x=".5" y=".5" width="{w-1:.0f}" height="{h-1:.0f}" rx="10" fill="none" stroke="{BORDER}"/>')
    s.append("</svg>")
    return "\n".join(s)


def run(x, y, s, size, fill, attrs=""):
    """A monospace text run pinned to the CW grid, so covers and cursors line up in any font."""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" textLength="{len(s)*size*CW:.1f}" '
            f'lengthAdjust="spacing" xml:space="preserve"{attrs}>{escape(s)}</text>')


class Term:
    """Lays out terminal lines and schedules them: commands are typed, output fades in."""

    def __init__(self, x, size=15):
        self.x, self.size, self.cw = x, size, size * CW
        self.t = 0.3
        self.out, self.css = [], []

    def _type(self, x, y, s, size, cps, cursor_from=None):
        n = len(s); cw = size * CW; w = n * cw; dur = n / cps; k = len(self.css)
        self.css.append(f"@keyframes t{k}{{to{{transform:translateX({w:.1f}px)}}}}")
        g = [f'<g class="cover" style="animation:t{k} {dur:.2f}s steps({n}) {self.t:.2f}s forwards">',
             f'<rect x="{x - 1:.1f}" y="{y - size:.1f}" width="{w + cw + 2:.1f}" height="{size * 1.4:.1f}" fill="{BG}"/>']
        if cursor_from is not None:
            g.append(f'<rect class="on" x="{x:.1f}" y="{y - size * .82:.1f}" width="{cw:.1f}" height="{size * 1.05:.1f}" '
                     f'fill="{GREEN}" style="animation-duration:{self.t + dur + .2 - cursor_from:.2f}s;animation-delay:{cursor_from:.2f}s"/>')
        g.append("</g>")
        self.out.append("".join(g))
        self.t += dur

    def prompt(self, y, cmd=None, cps=14):
        cw = self.cw
        self.out.append(
            f'<text class="fade" style="animation-delay:{self.t:.2f}s" x="{self.x}" y="{y}" font-size="{self.size}" '
            f'textLength="{(len(HOST) + 3) * cw:.1f}" lengthAdjust="spacing">'
            f'<tspan fill="{GREEN}" font-weight="700">{HOST}</tspan><tspan fill="{MUTED}">:</tspan>'
            f'<tspan fill="{BLUE}">~</tspan><tspan fill="{TEXT}">$</tspan></text>')
        cx = self.x + (len(HOST) + 4) * cw
        if cmd is None:  # idle prompt: blinking cursor forever
            self.out.append(f'<rect class="blink" x="{cx:.1f}" y="{y - self.size * .82:.1f}" width="{cw:.1f}" '
                            f'height="{self.size * 1.05:.1f}" fill="{GREEN}" style="animation-delay:{self.t:.2f}s"/>')
            return
        self.out.append(run(cx, y, cmd, self.size, TEXT))
        shown = self.t
        self.t += .35
        self._type(cx, y, cmd, self.size, cps, cursor_from=shown)
        self.t += .25

    def typed(self, y, s, size, fill, cps=16, attrs=""):
        self.out.append(run(self.x, y, s, size, fill, attrs))
        self._type(self.x, y, s, size, cps)
        self.t += .1

    def echo(self, y, s, fill, size=None, gap=.12):
        self.out.append(run(self.x, y, s, size or self.size, fill, f' class="fade" style="animation-delay:{self.t:.2f}s"'))
        self.t += gap


# ---- HERO ------------------------------------------------------------------

def hero():
    W, H = 880, 290
    t = Term(32)
    t.prompt(74, "whoami")
    i = len(t.out)
    t.typed(127, NAME, 42, BRIGHT, cps=18, attrs=' font-weight="700"')
    # the glow is a separate layer that lights up once the name is typed (a blur would bleed past the cover)
    t.out.insert(i, run(t.x, 127, NAME, 42, GREEN, f' font-weight="700" filter="url(#glow)" class="fade" '
                                                   f'style="animation-delay:{t.t:.2f}s;animation-duration:1.2s"'))
    t.echo(161, ROLE, GREEN, size=16, gap=.45)
    t.prompt(203, "cat focus.txt")
    t.echo(229, FOCUS, TEXT, gap=.35)
    t.prompt(267)
    glow = (f'<filter id="glow" x="-10%" y="-60%" width="120%" height="220%"><feGaussianBlur in="SourceAlpha" stdDeviation="7" result="b"/>'
            f'<feFlood flood-color="{GREEN}" flood-opacity=".5"/><feComposite in2="b" operator="in"/></filter>')
    return window(W, H, f"{HOST}: ~", t.out, "".join(t.css), glow)


# ---- PORTRAIT --------------------------------------------------------------

def portrait():
    path = os.path.join(OUT, "portrait.txt")
    if not os.path.exists(path):
        return None
    rows = open(path, encoding="utf-8").read().rstrip("\n").split("\n")
    cols = max(len(r) for r in rows)
    size, pad = 10, 18
    cw = size * CW
    lh = cw * 1.912  # glyph cell aspect used by make_ascii.py
    W = cols * cw + 2 * pad
    H = BAR + 2 * pad + len(rows) * lh
    rnd = random.Random(42)
    ramp = "-=+*#%@"
    body = []
    for r, line in enumerate(rows):
        line = line.ljust(cols)
        y = BAR + pad + r * lh + size * .8
        t = .2 + r * .04
        noise = "".join(" " if ch == " " else rnd.choice(ramp) for ch in line)
        body.append(run(pad, y, noise, size, GREEN, f' class="flash" style="animation-delay:{t:.2f}s"'))
        body.append(run(pad, y, line, size, TEXT, f' class="fade" style="animation-delay:{t + .3:.2f}s"'))
    body.append(f'<rect class="scan" x="0" y="-70" width="{W:.0f}" height="70" fill="url(#beam)"/>')
    css = (".flash{opacity:0;animation:flash .7s linear}"
           "@keyframes flash{25%{opacity:1}to{opacity:0}}"
           f".scan{{animation:scan 6s linear {.6 + len(rows) * .04:.2f}s infinite}}"
           f"@keyframes scan{{to{{transform:translateY({H + 70:.0f}px)}}}}")
    defs = (f'<pattern id="crt" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".22"/></pattern>'
            f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>'
            f'<stop offset=".85" stop-color="{GREEN}" stop-opacity=".10"/><stop offset="1" stop-color="{GREEN}" stop-opacity=".35"/></linearGradient>')
    body.append(f'<rect x="0" y="{BAR}" width="{W:.0f}" height="{H:.0f}" fill="url(#crt)"/>')
    return window(W, H, "portrait.txt", body, css, defs)


# ---- CONTRIBUTIONS ---------------------------------------------------------

def heatmap(days):
    vals = list(days.items())
    mx = max(v for _, v in vals) or 1
    cell, gap = 12, 3
    pitch = cell + gap
    first = date.fromisoformat(vals[0][0])
    offset = (first.weekday() + 1) % 7            # Sunday = 0
    weeks = (len(vals) + offset + 6) // 7
    W = 880
    left = (W - (weeks * pitch - gap)) / 2 + 14
    top = BAR + 40
    H = top + 7 * pitch + 48
    body = []
    # month labels: at the first column of each month, skipping labels that would collide
    last_m, last_x = None, -99
    for i, (k, _) in enumerate(vals):
        d = date.fromisoformat(k)
        idx = i + offset
        if idx % 7 and i: continue
        col = idx // 7
        if d.month != last_m and col - last_x >= 3:
            body.append(f'<text class="fade" style="animation-delay:{.2 + col * .018:.2f}s" x="{left + col * pitch:.1f}" '
                        f'y="{top - 10}" font-size="10" fill="{MUTED}">{d.strftime("%b")}</text>')
            last_x = col
        last_m = d.month
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        body.append(f'<text x="{left - 32:.1f}" y="{top + r * pitch + 10}" font-size="10" fill="{MUTED}">{name}</text>')
    for i, (k, v) in enumerate(vals):
        idx = i + offset
        x = left + (idx // 7) * pitch
        y = top + (idx % 7) * pitch
        body.append(f'<rect class="cell" style="animation-delay:{.2 + (idx // 7) * .018:.3f}s" x="{x:.1f}" y="{y}" '
                    f'width="{cell}" height="{cell}" rx="2.5" fill="{GREENS[level(v, mx)]}"/>')
    # today: a ring that keeps pulsing
    idx = len(vals) - 1 + offset
    x = left + (idx // 7) * pitch; y = top + (idx % 7) * pitch
    body.append(f'<rect class="pulse" x="{x - 2:.1f}" y="{y - 2}" width="{cell + 4}" height="{cell + 4}" rx="4" '
                f'fill="none" stroke="{GREEN}" stroke-width="1.5"/>')
    total = sum(v for _, v in vals)
    ly = top + 7 * pitch + 24
    end = .2 + weeks * .018
    body.append(f'<text class="fade" style="animation-delay:{end:.2f}s" x="{left:.1f}" y="{ly}" font-size="12" fill="{TEXT}">'
                f'<tspan fill="{GREEN}" font-weight="700">{total:,}</tspan> contributions in the last year</text>')
    lx = left + weeks * pitch - gap - 5 * (cell + 3) - 62
    body.append(f'<text x="{lx:.1f}" y="{ly}" font-size="10" fill="{MUTED}">Less</text>')
    for i, c in enumerate(GREENS):
        body.append(f'<rect x="{lx + 30 + i * (cell + 3):.1f}" y="{ly - 10}" width="{cell}" height="{cell}" rx="2.5" fill="{c}"/>')
    body.append(f'<text x="{lx + 34 + 5 * (cell + 3):.1f}" y="{ly}" font-size="10" fill="{MUTED}">More</text>')
    css = (".cell{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.8,.3,1.3) both}"
           "@keyframes pop{from{opacity:0;transform:scale(.3)}}")
    return window(W, H, "contributions.sh — last 12 months", body, css)


# ---- STATS -----------------------------------------------------------------

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

    W, H = 640, BAR + 330
    body = []
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
        y = BAR + 14 + (i // 3) * (chh + gy)
        body.append(f'<g class="rise" style="animation-delay:{.2 + i * .08:.2f}s">'
                    f'<rect x="{x}" y="{y}" width="{cw}" height="{chh}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>'
                    f'<text x="{x+10}" y="{y+16}" font-size="10" fill="{MUTED}">$ {lab}</text>'
                    f'<text x="{x+10}" y="{y+40}" font-size="22" font-weight="700" fill="{GREEN}">{val}</text>'
                    f'<text x="{x+10}" y="{y+55}" font-size="9" fill="{MUTED}">{sub}</text></g>')

    # monthly bars
    by = BAR + 168
    body.append(f'<g class="rise" style="animation-delay:.6s">'
                f'<rect x="14" y="{by}" width="{W-28}" height="{H-by-14}" rx="6" fill="{PANEL}" stroke="{BORDER}"/>'
                f'<text x="24" y="{by+18}" font-size="10" fill="{MUTED}">$ contributions / month</text></g>')
    mx = max(months.values()) or 1
    n = len(months)
    bw = (W - 28 - 40) / n
    base, ph = H - 36, 90
    for i, (m, v) in enumerate(months.items()):
        hh = max(2, ph * v / mx) if v else 2
        x = 34 + i * bw
        d = .8 + i * .05
        body.append(f'<rect class="bar" style="animation-delay:{d:.2f}s" x="{x:.1f}" y="{base-hh:.1f}" width="{bw-8:.1f}" '
                    f'height="{hh:.1f}" rx="2" fill="{GREEN}" opacity="{0.45 + 0.55*v/mx:.2f}"/>')
        lbl = date.fromisoformat(m + "-01").strftime("%b")[0]
        body.append(f'<text x="{x + (bw-8)/2:.1f}" y="{base+13}" font-size="9" text-anchor="middle" fill="{MUTED}">{lbl}</text>')
        if v == mx:
            body.append(f'<text class="fade" style="animation-delay:{d + .6:.2f}s" x="{x + (bw-8)/2:.1f}" y="{base-hh-5:.1f}" '
                        f'font-size="9" text-anchor="middle" fill="{TEXT}">{v:,}</text>')
    css = (".bar{transform-box:fill-box;transform-origin:bottom;animation:grow .8s cubic-bezier(.2,.8,.2,1) both}"
           "@keyframes grow{from{transform:scaleY(0)}}")
    updated = "updated " + datetime.now(timezone.utc).strftime("%b %-d")
    return window(W, H, "stats.sh", body, css, status=updated)


# ---- STACK -----------------------------------------------------------------

def stack():
    size, lh = 15, 26
    W = 880
    t = Term(32, size)
    y = BAR + 36
    t.prompt(y, "cat stack.json")
    t.t += .1
    cw = size * CW
    keyw = max(len(k) for k, _ in STACK) + 3  # "key": padded so the arrays line up
    lines = [[("{", MUTED)]]
    for i, (k, items) in enumerate(STACK):
        parts = [("  ", TEXT), (f'"{k}"', KEY), (":", MUTED), (" " * (keyw - len(k) - 2), TEXT), ("[", MUTED)]
        for j, it in enumerate(items):
            parts.append((f'"{it}"', STR))
            if j < len(items) - 1: parts.append((", ", MUTED))
        parts.append(("]" + ("," if i < len(STACK) - 1 else ""), MUTED))
        lines.append(parts)
    lines.append([("}", MUTED)])
    for parts in lines:
        y += lh
        s = "".join(p for p, _ in parts)
        spans = "".join(f'<tspan fill="{c}">{escape(p)}</tspan>' for p, c in parts)
        t.out.append(f'<text class="rise" style="animation-delay:{t.t:.2f}s" x="{t.x}" y="{y}" font-size="{size}" '
                     f'textLength="{len(s) * cw:.1f}" lengthAdjust="spacing" xml:space="preserve">{spans}</text>')
        t.t += .09
    t.t += .2
    y += lh + 4
    t.prompt(y)
    return window(W, y + 23, "stack.json", t.out, "".join(t.css))


if __name__ == "__main__":
    days = fetch_days()
    os.makedirs(OUT, exist_ok=True)
    out = {"hero.svg": hero(), "portrait.svg": portrait(), "contributions.svg": heatmap(days),
           "stats.svg": stats_card(days), "stack.svg": stack()}
    for name, svg in out.items():
        if svg:
            with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
                f.write(svg)
    print("ok", len(days), "days")

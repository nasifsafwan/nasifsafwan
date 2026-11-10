"""Generate retro-desktop SVG art for the GitHub profile README (light + dark)."""
import base64, io, json, os, sys
from fontTools.ttLib import TTFont
from fontTools import subset

SCR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCR)
OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)
ART = json.load(open(os.path.join(SCR, "art.json")))

THEMES = {
    "dark": dict(
        d0="#24262b", d1="#18191c", d2="#0f1012", sheen="rgba(0,255,102,.07)", dot="#ffffff", dot_op=".035",
        frame="#2a2b2f", frame_hi="#3b3c41", frame_lo="#18191b", edge="#0b0b0c", well="#1c1d20", rule="#2c2d31",
        ridge_a="#4a4b51", ridge_b="#18191b", ink="#ecebe6", muted="#a9a8a2", hl="#00e05c",
        sig1="#f5f5f5", g1="#00FF66", g2="#00cc88", glow="rgba(0,255,102,.18)",
        px={"#": "#e6e5e0", "w": "#2c2d31", "g": "#4a4c52", "a": "#00FF66"},
        folder={"w": "#1d4630", "g": "#2f6b49"}, label="#e9e8e3", shadow="#000000", shadow_op=".55",
    ),
    "light": dict(
        d0="#fffefb", d1="#f7f4ee", d2="#ece8e0", sheen="rgba(255,255,255,.9)", dot="#000000", dot_op=".05",
        frame="#f4f2ed", frame_hi="#ffffff", frame_lo="#d6d2c9", edge="#bdb8ae", well="#fffefc", rule="#ebe7df",
        ridge_a="#ffffff", ridge_b="#dad6cd", ink="#1b1c1e", muted="#5a5c60", hl="#00873f",
        sig1="#17181a", g1="#00b85a", g2="#00977a", glow="rgba(0,190,90,.14)",
        px={"#": "#2a2b2e", "w": "#ffffff", "g": "#d8d4cb", "a": "#00a84f"},
        folder={"w": "#dcf4e5", "g": "#a8dcbd"}, label="#2b2c2f", shadow="#46381f", shadow_op=".18",
    ),
}

UI_CHARS = "".join(chr(c) for c in range(32, 127)) + "—·’▸•©"


_FONT_CACHE = {}


def font_b64(path, text):
    """Subset + embed a font. Deterministic (no timestamps) so daily builds only change when content does."""
    key = (path, text)
    if key not in _FONT_CACHE:
        f = TTFont(path, recalcTimestamp=False)
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        s_ = subset.Subsetter(opts)
        s_.populate(text=text)
        s_.subset(f)
        f["head"].modified = f["head"].created
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf, reorderTables=True)
        _FONT_CACHE[key] = base64.b64encode(buf.getvalue()).decode()
    return _FONT_CACHE[key]


BARLOW = os.path.join(SCR, "fonts/barlow-700.woff2")
PRESS = os.path.join(SCR, "fonts/PressStart2P-Regular.woff2")
_bar = TTFont(BARLOW)
_upm = _bar["head"].unitsPerEm
_cmap = _bar.getBestCmap()
_hmtx = _bar["hmtx"]


def tw(text, size):
    """Text width in Barlow 700 at a given px size."""
    return sum(_hmtx[_cmap.get(ord(ch), _cmap[32])][0] for ch in text) * size / _upm


def css_fonts(press=False, press_text=None):
    out = "@font-face{font-family:B;src:url(data:font/woff2;base64,%s) format('woff2')}" % font_b64(BARLOW, UI_CHARS)
    if press or press_text:
        out += "@font-face{font-family:P;src:url(data:font/woff2;base64,%s) format('woff2')}" % font_b64(PRESS, press_text or "NASIF SAFWAN")
    return f"<style>{out}text{{font-family:B,'Barlow','Helvetica Neue',Arial,sans-serif;font-weight:700}}.p{{font-family:P,'Press Start 2P',monospace;font-weight:400}}</style>"


def icon(name, x, y, scale, t, folderish=False):
    rows = ART[name]
    pal = dict(t["px"])
    if folderish:
        pal.update(t["folder"])
    parts = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            ch = row[c]
            if ch in pal:
                e = c
                while e < len(row) and row[e] == ch:
                    e += 1
                parts.append(f'<rect x="{x + c * scale:g}" y="{y + r * scale:g}" width="{(e - c) * scale:g}" height="{scale:g}" fill="{pal[ch]}"/>')
                c = e
            else:
                c += 1
    return "".join(parts)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def defs_common(t, w, h):
    return f'''<defs>
<radialGradient id="desk" cx="50%" cy="28%" r="90%"><stop offset="0" stop-color="{t['d0']}"/><stop offset=".5" stop-color="{t['d1']}"/><stop offset="1" stop-color="{t['d2']}"/></radialGradient>
<radialGradient id="sheen" cx="50%" cy="42%" r="45%"><stop offset="0" stop-color="{t['sheen']}"/><stop offset="1" stop-color="{t['sheen']}" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="8" height="8" patternUnits="userSpaceOnUse"><rect x="0" y="0" width="1" height="1" fill="{t['dot']}" fill-opacity="{t['dot_op']}"/></pattern>
<linearGradient id="sig" x1="0" x2="1"><stop offset="0" stop-color="{t['g1']}"/><stop offset="1" stop-color="{t['g2']}"/></linearGradient>
<filter id="sh" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="{t['shadow']}" flood-opacity="{t['shadow_op']}"/></filter>
</defs>'''


def titlebar(t, x, y, w, title, h=28):
    """Classic window title bar: close box, pinstripes, centered title, zoom box."""
    tw_ = tw(title, 14)
    cx = x + w / 2
    gap = 14
    stripes = []
    for i in range(4):
        yy = y + 9 + i * 3
        for (sx, ex) in ((x + 34, cx - tw_ / 2 - gap), (cx + tw_ / 2 + gap, x + w - 34)):
            if ex > sx:
                stripes.append(f'<rect x="{sx:g}" y="{yy}" width="{ex - sx:g}" height="1" fill="{t["ridge_a"]}"/><rect x="{sx:g}" y="{yy + 1}" width="{ex - sx:g}" height="1" fill="{t["ridge_b"]}"/>')
    box = lambda bx: f'<rect x="{bx}" y="{y + 7.5}" width="13" height="13" rx="2" fill="{t["well"]}" stroke="{t["edge"]}"/>'
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{t["frame"]}"/>'
            + "".join(stripes) + box(x + 12) + box(x + w - 25)
            + f'<text x="{cx:g}" y="{y + 19}" font-size="14" fill="{t["ink"]}" text-anchor="middle">{esc(title)}</text>')


def bar(t, title, meta=""):
    W, H = 1000, 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">', css_fonts()]
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="{t["frame"]}" stroke="{t["edge"]}"/>')
    # scale up the titlebar into 40px
    tw_ = tw(title, 16)
    cx = W / 2
    for i in range(5):
        yy = 11 + i * 4
        for (sx, ex) in ((44, cx - tw_ / 2 - 18), (cx + tw_ / 2 + 18, W - 44 - (tw(meta, 13) + 18 if meta else 0))):
            if ex > sx:
                s.append(f'<rect x="{sx:g}" y="{yy}" width="{ex - sx:g}" height="1" fill="{t["ridge_a"]}"/><rect x="{sx:g}" y="{yy + 1}" width="{ex - sx:g}" height="1" fill="{t["ridge_b"]}"/>')
    s.append(f'<rect x="14" y="11" width="18" height="18" rx="3" fill="{t["well"]}" stroke="{t["edge"]}"/>')
    s.append(f'<text x="{cx:g}" y="26" font-size="16" fill="{t["ink"]}" text-anchor="middle">{esc(title)}</text>')
    if meta:
        s.append(f'<text x="{W - 44}" y="25.5" font-size="13" fill="{t["hl"]}" text-anchor="end">{esc(meta)}</text>')
    s.append(f'<rect x="{W - 32}" y="11" width="18" height="18" rx="3" fill="{t["well"]}" stroke="{t["edge"]}"/><rect x="{W - 28}" y="15" width="10" height="10" fill="none" stroke="{t["edge"]}"/>')
    s.append("</svg>")
    return "".join(s)


def chip(t, ic, label):
    fs = 13.5
    W = round(12 + 16 + 8 + tw(label, fs) + 14)
    H = 34
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">', css_fonts()]
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="5" fill="{t["frame"]}" stroke="{t["edge"]}"/><rect x="1.5" y="1.5" width="{W - 3}" height="1" fill="{t["frame_hi"]}"/>')
    s.append(icon(ic, 12, 9, 1, t))
    s.append(f'<text x="36" y="22" font-size="{fs}" fill="{t["ink"]}">{esc(label)}</text></svg>')
    return "".join(s)



# ---- animated banner + footer (spliced into gen.py) ----
MOTION = "@media (prefers-reduced-motion:no-preference){%s}"

ARROW = [  # classic pixel pointer, 11x17; '#' outline, 'w' fill
    "#..........", "##.........", "#w#........", "#ww#.......", "#www#......", "#wwww#.....",
    "#wwwww#....", "#wwwwww#...", "#wwwwwww#..", "#wwwwwwww#.", "#wwwww#####", "#ww#ww#....",
    "#w#.#ww#...", "##..#ww#...", "#....#ww#..", ".....#ww#..", "......##...",
]


def sprite(rows, x, y, s, pal):
    out = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            ch = row[c]
            if ch in pal:
                e = c
                while e < len(row) and row[e] == ch:
                    e += 1
                out.append(f'<rect x="{x + c * s:g}" y="{y + r * s:g}" width="{(e - c) * s:g}" height="{s:g}" fill="{pal[ch]}"/>')
                c = e
            else:
                c += 1
    return "".join(out)


def kf(name, frames):
    """frames: list of (pct, css) -> @keyframes block."""
    return "@keyframes %s{%s}" % (name, "".join(f"{p:.2f}%{{{c}}}" for p, c in frames))


def typing_css(phrases, fs, start_x):
    """Cover rect + cursor slide per character; each phrase fades in only during its window."""
    CH, HOLD, DEL, GAP = 0.055, 2.2, 0.022, 0.35
    segs, t = [], 0.0
    for p in phrases:
        ws = [0.0]
        for ch in p:
            ws.append(ws[-1] + tw(ch, fs))
        segs.append((t, ws))
        t += len(p) * CH + HOLD + len(p) * DEL + GAP
    total = t
    pct = lambda x: x / total * 100
    cover, caret, vis = [], [], [[] for _ in phrases]
    for k, (t0, ws) in enumerate(segs):
        n = len(ws) - 1
        for i in range(n + 1):  # type
            tt = t0 + i * CH
            cover.append((pct(tt), f"transform:translateX({ws[i]:.1f}px)"))
            caret.append((pct(tt), f"transform:translateX({ws[i]:.1f}px)"))
        t_hold_end = t0 + n * CH + HOLD
        for i in range(n, -1, -1):  # delete
            tt = t_hold_end + (n - i) * DEL
            cover.append((pct(tt), f"transform:translateX({ws[i]:.1f}px)"))
            caret.append((pct(tt), f"transform:translateX({ws[i]:.1f}px)"))
        t_end = t_hold_end + n * DEL + GAP
        for j in range(len(phrases)):
            vis[j].append((pct(t0), f"opacity:{1 if j == k else 0}"))
        vis[k].append((pct(t_end - 0.01), "opacity:0"))
    cover.append((100, "transform:translateX(0px)"))
    caret.append((100, "transform:translateX(0px)"))
    css = kf("cov", cover) + kf("car", caret)
    css += "".join(kf(f"ph{j}", v + [(100, "opacity:0")]) for j, v in enumerate(vis))
    run = f"{total:.2f}s step-end infinite"
    css += f".cov{{animation:cov {run}}}.car{{animation:car {run},blink 1s step-end infinite}}"
    css += "".join(f".ph{j}{{animation:ph{j} {run}}}" for j in range(len(phrases)))
    return css


def banner(t, mode):
    W, H = 1000, 400
    L = 15.0  # scenario loop seconds
    BOOT = 2.0
    s = []
    css = []

    # ---------------- static desktop (same as before) ----------------
    s.append(f'<rect width="{W}" height="{H}" rx="12" fill="url(#desk)"/><rect width="{W}" height="{H}" rx="12" fill="url(#dots)"/><rect width="{W}" height="{H}" fill="url(#sheen)"/>')
    s.append(f'<path d="M12 0H{W - 12}a12 12 0 0 1 12 12V28H0V12A12 12 0 0 1 12 0z" fill="{t["frame"]}"/><rect y="28" width="{W}" height="1" fill="{t["edge"]}"/>')
    s.append(icon("ns", 13, 8.5, 1.5, t))
    mx = 44
    for item in ["File", "View", "Projects", "Research", "Certificates", "Contact"]:
        s.append(f'<text x="{mx}" y="19.5" font-size="13.5" fill="{t["ink"]}">{item}</text>')
        mx += tw(item, 13.5) + 22
    s.append(f'<text x="{W - 44}" y="19.5" font-size="13" fill="{t["muted"]}" text-anchor="end">Dhaka · UTC+6</text>')
    s.append(icon("moon" if mode == "dark" else "sun", W - 32, 8.5, 1.1, t))

    wx, wy, ww, wh = 34, 70, 236, 182
    s.append(f'<g filter="url(#sh)"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="4" fill="{t["frame"]}" stroke="{t["edge"]}"/></g>')
    s.append(titlebar(t, wx + 1, wy + 1, ww - 2, "About This Computer"))
    s.append(f'<rect x="{wx + 8}" y="{wy + 32}" width="{ww - 16}" height="{wh - 40}" rx="2" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    s.append(icon("mac", wx + 18, wy + 44, 2, t))
    s.append(f'<text x="{wx + 60}" y="{wy + 57}" font-size="15" fill="{t["ink"]}">Nasif Safwan</text>')
    s.append(f'<text x="{wx + 60}" y="{wy + 74}" font-size="11.5" fill="{t["muted"]}">AI Researcher · Dhaka</text>')
    for i, (ic, txt) in enumerate([("brain", "Medical AI · NeuroAI"), ("doc", "15 papers · 5 journals"), ("qrcode", "Shipping at Ledgercross")]):
        ry = wy + 96 + i * 26
        s.append(f'<rect x="{wx + 16}" y="{ry + 21}" width="{ww - 32}" height="1" fill="{t["rule"]}"/>')
        s.append(icon(ic, wx + 18, ry + 1, 1.1, t))
        s.append(f'<text x="{wx + 42}" y="{ry + 14}" font-size="12.5" fill="{t["ink"]}">{esc(txt)}</text>')

    cx = W / 2 + 40
    s.append(f'<text class="p" x="{cx}" y="182" font-size="58" fill="{t["sig1"]}" text-anchor="middle" letter-spacing="2">NASIF</text>')
    s.append(f'<text class="p" x="{cx}" y="252" font-size="58" fill="url(#sig)" text-anchor="middle" letter-spacing="2">SAFWAN</text>')

    # ---------------- typing pill, cycling phrases ----------------
    phrases = ["AI researcher · builder · professional overthinker",
               "Teaching machines to read brain scans.",
               "Shipping anti-counterfeit AI at Ledgercross.",
               "Co-founded a lab. Sleep is under review."]
    fs = 15
    maxw = max(tw(p, fs) for p in phrases)
    pw = maxw + 64
    px_, py = cx - pw / 2, 288
    tx = px_ + 34
    s.append(f'<rect x="{px_:g}" y="{py}" width="{pw:g}" height="34" rx="17" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    s.append(f'<circle class="led" cx="{px_ + 20:g}" cy="{py + 17}" r="4.5" fill="{t["hl"]}"/>')
    s.append(f'<clipPath id="pill"><rect x="{tx - 2:g}" y="{py + 2}" width="{maxw + 24:g}" height="30"/></clipPath><g clip-path="url(#pill)">')
    for j, p in enumerate(phrases):
        op = '' if j == 0 else ' opacity="0"'
        s.append(f'<text class="ph{j}" x="{tx:g}" y="{py + 22}" font-size="{fs}" fill="{t["ink"]}"{op}>{esc(p)}</text>')
    # cover hides untyped text: sits after the text by default (static fallback = phrase 0 fully shown)
    w0 = tw(phrases[0], fs)
    s.append(f'<g class="cov"><rect x="{tx:g}" y="{py + 3}" width="{maxw + 30:g}" height="28" fill="{t["well"]}" transform="translate({w0:.1f} 0)"/></g>')
    s.append(f'<g class="car"><rect x="{tx + 2:g}" y="{py + 9}" width="2" height="17" fill="{t["hl"]}" transform="translate({w0:.1f} 0)"/></g>')
    s.append("</g>")
    css.append(MOTION % (typing_css(phrases, fs, tx)
               + kf("blink", [(0, "opacity:1"), (50, "opacity:0")])
               + ".led{animation:led 2.4s ease-in-out infinite}" + kf("led", [(0, "opacity:1"), (50, "opacity:.3"), (100, "opacity:1")])
               # cover/caret rects carry a static translate for the fallback; zero it while animating
               + ".cov rect,.car rect{transform:none}"))

    # ---------------- desktop icons ----------------
    icons = [("disk", "Nasif HD", False), ("folder", "Research", True), ("folder", "Projects", True), ("doc", "Nasif_CV.pdf", False), ("mail", "Say Hello", False)]
    col = [(W - 160, 56), (W - 76, 56), (W - 160, 140), (W - 76, 140), (W - 118, 224)]
    for (ic, lab, fo), (ix, iy) in zip(icons, col):
        if lab == "Research":
            lw = tw(lab, 12.5) + 10
            # selection state: inverse label + darkened icon (hidden unless animating)
            s.append(f'<g class="sel" opacity="0"><rect x="{ix - 19}" y="{iy - 3}" width="38" height="38" rx="3" fill="{t["hl"]}" fill-opacity=".22"/><rect x="{ix - lw / 2:g}" y="{iy + 39}" width="{lw:g}" height="16" rx="2" fill="{t["hl"]}"/></g>')
            s.append(icon(ic, ix - 16, iy, 2, t, fo))
            s.append(f'<text x="{ix}" y="{iy + 50}" font-size="12.5" fill="{t["label"]}" text-anchor="middle">{lab}</text>')
            s.append(f'<text class="sel" opacity="0" x="{ix}" y="{iy + 50}" font-size="12.5" fill="{"#06140b" if mode == "dark" else "#ffffff"}" text-anchor="middle">{lab}</text>')
        else:
            s.append(icon(ic, ix - 16, iy, 2, t, fo))
            s.append(f'<text x="{ix}" y="{iy + 50}" font-size="12.5" fill="{t["label"]}" text-anchor="middle">{lab}</text>')
    s.append(icon("trash", W - 92, H - 92, 2, t))
    s.append(f'<text x="{W - 76}" y="{H - 30}" font-size="12.5" fill="{t["label"]}" text-anchor="middle">Trash</text>')

    # ---------------- zoom-open window scenario ----------------
    FX, FY, FW, FH = W - 92, 56, 32, 32          # folder icon box
    RX, RY, RW, RH = 296, 80, 428, 198            # window box
    pct = lambda sec: sec / L * 100
    # zoom rects
    for i in range(4):
        s.append(f'<rect class="zo z{i}" x="0" y="0" width="1" height="1" fill="none" stroke="{t["ink"]}" stroke-width="1.5" stroke-dasharray="3 2" vector-effect="non-scaling-stroke" opacity="0"/>')
    # window
    s.append(f'<g class="win" opacity="0"><g filter="url(#sh)"><rect x="{RX}" y="{RY}" width="{RW}" height="{RH}" rx="4" fill="{t["frame"]}" stroke="{t["edge"]}"/></g>')
    s.append(titlebar(t, RX + 1, RY + 1, RW - 2, "Research"))
    s.append(f'<rect x="{RX + 8}" y="{RY + 32}" width="{RW - 16}" height="{RH - 66}" rx="2" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    papers = [("T3SSLNet", "IEEE Access · 2025"), ("Hi-TGNet", "Scientific Reports · 2026"),
              ("KbFL-XAI", "Elsevier BEA · 2025"), ("OpthaNet", "IET & Wiley · 2026")]
    for i, (n, v) in enumerate(papers):
        ry = RY + 38 + i * 29
        s.append(f'<rect class="row r{i}" x="{RX + 11}" y="{ry}" width="{RW - 22}" height="27" rx="2" fill="{t["hl"]}" fill-opacity=".18" opacity="0"/>')
        s.append(icon("paper", RX + 18, ry + 5, 1.1, t))
        s.append(f'<text x="{RX + 42}" y="{ry + 18}" font-size="13.5" fill="{t["ink"]}">{esc(n)}</text>')
        s.append(f'<text x="{RX + RW - 22}" y="{ry + 18}" font-size="12" fill="{t["muted"]}" text-anchor="end">{esc(v)}</text>')
    s.append(f'<text x="{RX + 14}" y="{RY + RH - 13}" font-size="12.5" fill="{t["hl"]}">15 papers · 5 journals · 7 conferences</text>')
    s.append(f'<text x="{RX + RW - 14}" y="{RY + RH - 13}" font-size="12.5" fill="{t["muted"]}" text-anchor="end">Scholar ▸</text></g>')

    # pointer
    REST = (612, 352)
    s.append(f'<g class="ptr"><g class="ptrc">{sprite(ARROW, 0, 0, 1.6, {"#": "#0b0b0c" if mode == "dark" else "#1b1c1e", "w": "#ffffff"})}</g></g>')
    s.append(f'<style>.ptr{{transform:translate({REST[0]}px,{REST[1]}px)}}</style>')

    TIP_F = (FX + 20, FY + 20)                    # over the folder
    rowpts = [(RX + 180, RY + 52 + i * 29) for i in range(4)]
    CLOSE = (RX + 16, RY + 12)                    # close box
    e = "animation-timing-function:cubic-bezier(.45,.05,.3,1)"
    pos = lambda p: f"transform:translate({p[0]}px,{p[1]}px);{e}"
    tl = [(0, REST), (1.5, TIP_F), (2.4, TIP_F), (4.1, rowpts[0]), (5.0, rowpts[1]), (5.9, rowpts[2]), (6.8, rowpts[3]),
          (7.8, CLOSE), (8.6, CLOSE), (10.4, REST), (L, REST)]
    css_s = kf("ptr", [(pct(a), pos(p)) for a, p in tl])
    # double-click on folder (1.6–2.1s) and single click on close (8.0s)
    clicks = [1.65, 1.95, 8.05]
    cf = [(0, "transform:scale(1)")]
    for c in clicks:
        cf += [(pct(c), "transform:scale(1)"), (pct(c + 0.06), "transform:scale(.86)"), (pct(c + 0.14), "transform:scale(1)")]
    css_s += kf("clk", cf + [(100, "transform:scale(1)")])
    # selection on from first click until window closes
    css_s += kf("sel", [(0, "opacity:0"), (pct(1.7), "opacity:1"), (pct(8.3), "opacity:1"), (pct(8.4), "opacity:0"), (100, "opacity:0")])

    def box(b):
        x, y, w_, h_ = b
        return f"transform:translate({x}px,{y}px) scale({w_},{h_})"
    zin, zout = 2.15, 8.15
    for i in range(4):
        d = i * 0.07
        css_s += kf(f"z{i}", [(0, "opacity:0;" + box((FX, FY, FW, FH))),
                              (pct(zin + d), "opacity:1;" + box((FX, FY, FW, FH))),
                              (pct(zin + d + 0.32), "opacity:1;" + box((RX, RY, RW, RH))),
                              (pct(zin + d + 0.36), "opacity:0;" + box((RX, RY, RW, RH))),
                              (pct(zout + d), "opacity:0;" + box((RX, RY, RW, RH))),
                              (pct(zout + d + 0.01), "opacity:1;" + box((RX, RY, RW, RH))),
                              (pct(zout + d + 0.32), "opacity:1;" + box((FX, FY, FW, FH))),
                              (pct(zout + d + 0.36), "opacity:0;" + box((FX, FY, FW, FH))),
                              (100, "opacity:0;" + box((FX, FY, FW, FH)))])
    css_s += kf("win", [(0, "opacity:0"), (pct(zin + 0.5), "opacity:0"), (pct(zin + 0.55), "opacity:1"),
                        (pct(zout), "opacity:1"), (pct(zout + 0.05), "opacity:0"), (100, "opacity:0")])
    for i in range(4):
        a = 3.9 + i * 0.9
        css_s += kf(f"r{i}", [(0, "opacity:0"), (pct(a), "opacity:0"), (pct(a + 0.08), "opacity:1"),
                              (pct(a + 0.85), "opacity:1"), (pct(a + 0.9), "opacity:0"), (100, "opacity:0")])
    run = f"{L}s linear {BOOT + 0.6}s infinite"
    css_s += (f".ptr{{animation:ptr {run} both}}.ptrc{{transform-box:fill-box;transform-origin:0 0;animation:clk {run} both}}"
              f".sel{{animation:sel {run} both}}.win{{animation:win {run} both}}"
              + "".join(f".z{i}{{animation:z{i} {run} both}}" for i in range(4))
              + "".join(f".r{i}{{animation:r{i} {run} both}}" for i in range(4))
              + ".zo{transform-box:view-box;transform-origin:0 0}")
    css.append(MOTION % css_s)

    # ---------------- boot screen (plays once) ----------------
    boot_bg = "#0e0f11" if mode == "dark" else "#efece5"
    s.append(f'<g class="boot" opacity="0"><rect width="{W}" height="{H}" rx="12" fill="{boot_bg}"/>')
    s.append(icon("mac", W / 2 - 32, 120, 4, t))
    s.append(f'<text x="{W / 2}" y="222" font-size="16" fill="{t["ink"]}" text-anchor="middle">Booting up. Hang tight.</text>')
    s.append(f'<rect x="{W / 2 - 110}" y="240" width="220" height="12" rx="2" fill="none" stroke="{t["muted"]}"/>')
    s.append(f'<rect class="bootbar" x="{W / 2 - 108}" y="242" width="216" height="8" fill="{t["hl"]}"/>')
    s.append(f'<text x="{W / 2}" y="282" font-size="12.5" fill="{t["muted"]}" text-anchor="middle">Loading research, side projects and a questionable sleep schedule…</text></g>')
    css.append(MOTION % (kf("boot", [(0, "opacity:1"), (82, "opacity:1"), (100, "opacity:0;visibility:hidden")])
                         + kf("bar", [(0, "transform:scaleX(0)"), (20, "transform:scaleX(.25)"), (45, "transform:scaleX(.4)"),
                                      (70, "transform:scaleX(.85)"), (80, "transform:scaleX(1)"), (100, "transform:scaleX(1)")])
                         + f".boot{{animation:boot {BOOT}s ease-in 1 both}}.bootbar{{transform-box:fill-box;transform-origin:0 50%;animation:bar {BOOT}s steps(14,end) 1 both}}"))

    head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Nasif Safwan: AI researcher, builder, professional overthinker">',
            css_fonts(press=True), defs_common(t, W, H), "<style>" + "".join(css) + "</style>"]
    return "".join(head + s + ["</svg>"])


def footer(t):
    W, H = 1000, 46
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Dhaka, Bangladesh. Sleep is under review.">', css_fonts()]
    s.append("<style>" + MOTION % (kf("pole", [(0, "transform:translateX(0px)"), (100, "transform:translateX(-16px)")]) + ".pole{animation:pole .9s linear infinite}") + "</style>")
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="{t["frame"]}" stroke="{t["edge"]}"/>')
    s.append(icon("ns", 14, 17.5, 1.5, t))
    s.append(f'<text x="42" y="28" font-size="13.5" fill="{t["muted"]}">Dhaka, Bangladesh · nasifsafwan.me</text>')
    bw, bx = 150, W - 18 - 150
    lab = "Sleep is under review"
    s.append(f'<text x="{bx - 12}" y="28" font-size="13.5" fill="{t["ink"]}" text-anchor="end">{lab}</text>')
    s.append(f'<clipPath id="pb"><rect x="{bx + 2}" y="17" width="{bw - 4}" height="12"/></clipPath>')
    s.append(f'<rect x="{bx}" y="15" width="{bw}" height="16" rx="2" fill="{t["well"]}" stroke="{t["edge"]}"/>')
    stripes = "".join(f'<path d="M{bx + k * 16} 31 l8 -16 h8 l-8 16z" fill="{t["hl"]}"/>' for k in range(-1, bw // 16 + 3))
    s.append(f'<g clip-path="url(#pb)"><rect x="{bx}" y="15" width="{bw}" height="16" fill="{t["hl"]}" fill-opacity=".25"/><g class="pole">{stripes}</g></g>')
    s.append("</svg>")
    return "".join(s)


BARS = {
    "readme": ("Read Me — SimpleText", ""),
    "activity": ("Activity", "updated daily"),
    "research": ("Research", "15 papers · 5 journals"),
    "projects": ("Projects", "selected"),
    "toolkit": ("Control Panels", "the toolkit"),
}
CHIPS = {
    "portfolio": ("ns", "nasifsafwan.me"),
    "linkedin": ("linkedin", "LinkedIn"),
    "scholar": ("scholar", "Scholar"),
    "orcid": ("orcid", "ORCID"),
    "researchgate": ("researchgate", "ResearchGate"),
    "cv": ("cv", "CV"),
    "email": ("mail", "Email"),
}


# ======================= project windows =======================
import datetime as _dt
import urllib.request as _ur


def wrap(text, size, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if tw(trial, size) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


PROJECTS = [
    dict(key="ledgerscan", name="LedgerScan", icon="qrcode", cat="SUPPLY-CHAIN AUTHENTICITY", status="LIVE",
         desc="Scan a product, know if it's fake. On-chain product IDs plus an AI risk engine that flags shady scans in about 0.3 s.",
         stack=["React", "Fastify", "FastAPI", "Solidity", "Keycloak"], scene="scan"),
    dict(key="kyc", name="KYC Platform", icon="fingerprint", cat="IDENTITY · COMPUTER VISION", status="PRIVATE",
         desc="Serverless identity checks built for 10M+ monthly users: document OCR, face match with liveness, signed results over webhooks.",
         stack=["FastAPI", "InsightFace", "ONNX", "Cloud Run", "Terraform"], scene="match"),
    dict(key="zentra", name="Zentra", icon="shirt", cat="E-COMMERCE", status="LIVE",
         desc="Custom sportswear for teams across Bangladesh: pick a kit, add names, numbers and crests, order in one flow.",
         stack=["Next.js", "TypeScript", "Supabase", "Vercel"], scene="kit"),
    dict(key="houseledger", name="House Ledger", icon="house", cat="EXPENSE MANAGEMENT", status="LIVE",
         desc="Mess and hostel money without the arguments: meals, rent, shared bills, settlements and monthly analytics.",
         stack=["React", "Node.js", "MongoDB", "Vercel"], scene="split"),
    dict(key="argus", name="Argus", icon="detect", cat="SEO · AI AGENTS", status="CODE",
         desc="Give it a URL and keywords. Argus crawls the site with Playwright and scores content gaps with Gemini.",
         stack=["Next.js", "Playwright", "Gemini", "Supabase"], scene="radar"),
    dict(key="t3sslnet", name="T3SSLNet", icon="brain", cat="RESEARCH · MEDICAL AI", status="PAPER",
         desc="Triple-method self-supervised learning for brain tumor MRI: SimCLR, MoCo and BYOL views, one encoder. IEEE Access 2025.",
         stack=["PyTorch", "SimCLR", "MoCo", "BYOL"], scene="ssl"),
]


def scene(t, mode, kind, bx, by, bw, bh, uid):
    """Small animated pixel vignette inside the box. Static state = the finished frame."""
    s, css = [], []
    cx, cy = bx + bw / 2, by + bh / 2
    ink, hl, mut = t["ink"], t["hl"], t["muted"]
    dark_txt = "#06140b" if mode == "dark" else "#ffffff"
    if kind == "scan":
        q = 5
        qx, qy = cx - 40, by + 14
        s.append(icon("qrcode", qx, qy, q, t))
        s.append(f'<g class="{uid}l"><rect x="{qx - 6}" y="{qy}" width="92" height="2" fill="{hl}"/><rect x="{qx - 6}" y="{qy - 10}" width="92" height="10" fill="{hl}" fill-opacity=".14"/></g>')
        s.append(f'<g class="{uid}s"><g transform="rotate(-8 {cx} {by + bh - 22})"><rect x="{cx - 46}" y="{by + bh - 34}" width="92" height="22" rx="2" fill="none" stroke="{hl}" stroke-width="2"/>'
                 f'<text x="{cx}" y="{by + bh - 18}" font-size="13" fill="{hl}" text-anchor="middle" letter-spacing="2">GENUINE</text></g></g>')
        css.append(kf(f"{uid}l", [(0, "transform:translateY(0)"), (55, "transform:translateY(80px)"), (56, "transform:translateY(80px);opacity:0"), (100, "transform:translateY(80px);opacity:0")])
                   + kf(f"{uid}s", [(0, "opacity:0;transform:scale(1.6)"), (56, "opacity:0;transform:scale(1.6)"), (64, "opacity:1;transform:scale(1)"), (92, "opacity:1;transform:scale(1)"), (100, "opacity:0;transform:scale(1)")])
                   + f".{uid}l{{animation:{uid}l 3.2s cubic-bezier(.5,0,.5,1) infinite}}.{uid}s{{transform-box:fill-box;transform-origin:center;animation:{uid}s 3.2s ease-out infinite}}")
    elif kind == "match":
        # ID card
        ix, iy = bx + 12, cy - 30
        s.append(f'<rect x="{ix}" y="{iy}" width="66" height="46" rx="3" fill="{t["frame"]}" stroke="{ink}" stroke-opacity=".5"/>')
        s.append(f'<circle cx="{ix + 16}" cy="{iy + 18}" r="7" fill="{mut}"/><rect x="{ix + 6}" y="{iy + 28}" width="20" height="10" rx="5" fill="{mut}"/>')
        for k in range(3):
            s.append(f'<rect x="{ix + 32}" y="{iy + 12 + k * 9}" width="{26 - k * 6}" height="3" fill="{mut}" fill-opacity=".7"/>')
        # face frame with corner brackets
        fx, fy, fw = bx + bw - 66, cy - 36, 54
        s.append(icon("fingerprint", fx + 11, fy + 11, 2, t))
        for (x0, y0, dx, dy) in ((fx, fy, 1, 1), (fx + fw, fy, -1, 1), (fx, fy + fw, 1, -1), (fx + fw, fy + fw, -1, -1)):
            s.append(f'<path class="{uid}b" d="M{x0} {y0 + dy * 12}V{y0}H{x0 + dx * 12}" fill="none" stroke="{hl}" stroke-width="2.5"/>')
        s.append(f'<path class="{uid}d" d="M{ix + 70} {cy - 7}H{fx - 6}" stroke="{hl}" stroke-width="2" stroke-dasharray="4 4" fill="none"/>')
        s.append(f'<g class="{uid}c"><rect x="{cx - 38}" y="{by + bh - 30}" width="76" height="20" rx="10" fill="{hl}"/>'
                 f'<text x="{cx}" y="{by + bh - 15.5}" font-size="12" fill="{dark_txt}" text-anchor="middle">MATCH 98%</text></g>')
        css.append(kf(f"{uid}d", [(0, "stroke-dashoffset:24"), (100, "stroke-dashoffset:0")])
                   + kf(f"{uid}b", [(0, "opacity:.35"), (50, "opacity:1"), (100, "opacity:.35")])
                   + kf(f"{uid}c", [(0, "opacity:0"), (45, "opacity:0"), (52, "opacity:1"), (90, "opacity:1"), (100, "opacity:0")])
                   + f".{uid}d{{animation:{uid}d .6s linear infinite}}.{uid}b{{animation:{uid}b 1.2s ease-in-out infinite}}.{uid}c{{animation:{uid}c 3.6s step-end infinite}}")
    elif kind == "kit":
        sx, sy = cx - 40, by + 8
        s.append(icon("shirt", sx, sy, 5, dict(t, px=dict(t["px"], a=t["px"]["w"]))))
        nums = ["10", "07", "23"]
        for j, n in enumerate(nums):
            op = '' if j == 0 else ' opacity="0"'
            s.append(f'<text class="p {uid}n{j}" x="{cx}" y="{sy + 58}" font-size="16" fill="{hl}" text-anchor="middle"{op}>{n}</text>')
            css.append(kf(f"{uid}n{j}", [(0, "opacity:0"), (j * 33.3, "opacity:0"), (j * 33.3 + 0.1, "opacity:1"), (j * 33.3 + 33.2, "opacity:1"), (j * 33.3 + 33.3, "opacity:0"), (100, "opacity:0")])
                       + f".{uid}n{j}{{animation:{uid}n{j} 4.5s step-end infinite}}")
        names = ["SAFWAN", "RAHMAN", "JABIR"]
        for j, n in enumerate(names):
            op = '' if j == 0 else ' opacity="0"'
            s.append(f'<text class="{uid}n{j}" x="{cx}" y="{by + bh - 12}" font-size="12" fill="{mut}" text-anchor="middle" letter-spacing="3"{op}>{n}</text>')
    elif kind == "split":
        s.append(icon("house", cx - 32, by + 6, 4, t))
        segs = [("RENT", .4), ("MEALS", .3), ("BILLS", .2), ("WIFI", .1)]
        x0, yb, wb = bx + 14, by + bh - 40, bw - 28
        s.append(f'<rect x="{x0}" y="{yb}" width="{wb}" height="14" rx="2" fill="none" stroke="{mut}" stroke-opacity=".6"/>')
        acc = 0
        shades = [hl, t["g2"], t["g1"], mut]
        for k, (lab, frac) in enumerate(segs):
            w_ = wb * frac
            s.append(f'<rect class="{uid}g{k}" x="{x0 + acc + 1:.1f}" y="{yb + 2}" width="{w_ - 2:.1f}" height="10" fill="{shades[k]}"/>')
            css.append(kf(f"{uid}g{k}", [(0, "transform:scaleX(0)"), (k * 15, "transform:scaleX(0)"), (k * 15 + 14, "transform:scaleX(1)"), (92, "transform:scaleX(1)"), (100, "transform:scaleX(0)")])
                       + f".{uid}g{k}{{transform-box:fill-box;transform-origin:0 50%;animation:{uid}g{k} 4s ease-out infinite}}")
            acc += w_
        s.append(f'<text class="{uid}t" x="{cx}" y="{by + bh - 9}" font-size="12" fill="{hl}" text-anchor="middle" letter-spacing="2">SETTLED</text>')
        css.append(kf(f"{uid}t", [(0, "opacity:0"), (62, "opacity:0"), (66, "opacity:1"), (92, "opacity:1"), (100, "opacity:0")]) + f".{uid}t{{animation:{uid}t 4s step-end infinite}}")
    elif kind == "radar":
        r = 48
        ry_ = cy - 6
        for k in (1, 2, 3):
            s.append(f'<circle cx="{cx}" cy="{ry_}" r="{r * k / 3:.1f}" fill="none" stroke="{hl}" stroke-opacity=".35"/>')
        s.append(f'<path d="M{cx - r} {ry_}H{cx + r}M{cx} {ry_ - r}V{ry_ + r}" stroke="{hl}" stroke-opacity=".2"/>')
        s.append(f'<defs><linearGradient id="{uid}w" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{hl}" stop-opacity="0"/><stop offset="1" stop-color="{hl}" stop-opacity=".55"/></linearGradient></defs>')
        s.append(f'<g class="{uid}r"><path d="M{cx} {ry_}L{cx + r} {ry_}A{r} {r} 0 0 0 {cx + r * 0.5:.1f} {ry_ - r * 0.866:.1f}z" fill="url(#{uid}w)"/><path d="M{cx} {ry_}H{cx + r}" stroke="{hl}" stroke-width="2"/></g>')
        blips = [(30, 0.75), (140, 0.5), (230, 0.8), (310, 0.4)]
        for k, (ang, rad) in enumerate(blips):
            import math
            bxp = cx + r * rad * math.cos(math.radians(-ang))
            byp = ry_ + r * rad * math.sin(math.radians(-ang))
            s.append(f'<rect class="{uid}k{k}" x="{bxp - 3:.1f}" y="{byp - 3:.1f}" width="6" height="6" fill="{hl}"/>')
            # sweep rotates clockwise (positive deg in screen space); blip angle measured counter-clockwise
            hit = ((360 - ang) % 360) / 360 * 100
            css.append(kf(f"{uid}k{k}", [(0, "opacity:.15"), (hit, "opacity:.15"), (min(hit + 1, 99.9), "opacity:1"), (min(hit + 30, 99.95), "opacity:.15"), (100, "opacity:.15")])
                       + f".{uid}k{k}{{animation:{uid}k{k} 3s linear infinite}}")
        s.append(f'<text x="{cx}" y="{by + bh - 6}" font-size="12" fill="{mut}" text-anchor="middle" letter-spacing="1">GAP SCORE <tspan fill="{hl}">72</tspan></text>')
        css.append(kf(f"{uid}r", [(0, "transform:rotate(0deg)"), (100, "transform:rotate(360deg)")])
                   + f".{uid}r{{transform-box:view-box;transform-origin:{cx}px {ry_}px;animation:{uid}r 3s linear infinite}}")
    elif kind == "ssl":
        s.append(icon("brain", bx + 10, cy - 34, 4, t))
        labs = ["SimCLR", "MoCo", "BYOL"]
        for k, lab in enumerate(labs):
            yy = by + 16 + k * 34
            s.append(f'<rect x="{bx + bw - 66}" y="{yy}" width="56" height="24" rx="3" fill="{t["frame"]}" stroke="{mut}" stroke-opacity=".5"/>')
            s.append(f'<rect class="{uid}v{k}" x="{bx + bw - 66}" y="{yy}" width="56" height="24" rx="3" fill="{hl}" opacity="0"/>')
            s.append(f'<text x="{bx + bw - 38}" y="{yy + 16}" font-size="11.5" fill="{ink}" text-anchor="middle">{lab}</text>')
            s.append(f'<path class="{uid}v{k}" d="M{bx + 78} {cy - 2}L{bx + bw - 70} {yy + 12}" stroke="{hl}" stroke-width="1.5" stroke-dasharray="3 3" opacity="0"/>')
            css.append(kf(f"{uid}v{k}", [(0, "opacity:0"), (k * 25, "opacity:0"), (k * 25 + 2, "opacity:.45"), (k * 25 + 25, "opacity:.45"), (k * 25 + 27, "opacity:0"), (100, "opacity:0")])
                       + f".{uid}v{k}{{animation:{uid}v{k} 3.6s ease-in-out infinite}}")
    return "".join(s), MOTION % "".join(css)


def project_card(t, mode, p):
    W, H = 500, 264
    uid = "s" + p["key"][:4]
    bx, by, bw, bh = W - 178, 48, 160, 132
    art, css = scene(t, mode, p["scene"], bx, by, bw, bh, uid)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(p["name"])}: {esc(p["desc"])}">',
         css_fonts(press_text="0123456789"), defs_common(t, W, H), f"<style>{css}</style>"]
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="{t["frame"]}" stroke="{t["edge"]}"/>')
    s.append(titlebar(t, 1, 1, W - 2, p["name"] + ".app"))
    s.append(f'<rect x="8" y="32" width="{W - 16}" height="{H - 40}" rx="3" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    # scene box
    s.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="url(#desk)" stroke="{t["rule"]}"/><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="url(#dots)"/>')
    s.append(f'<svg x="0" y="0" width="{W}" height="{H}" overflow="visible"><clipPath id="{uid}cp"><rect x="{bx + 1}" y="{by + 1}" width="{bw - 2}" height="{bh - 2}" rx="2"/></clipPath><g clip-path="url(#{uid}cp)">{art}</g></svg>')
    # heading
    s.append(icon(p["icon"], 24, 50, 2, t))
    s.append(f'<text x="66" y="70" font-size="24" fill="{t["ink"]}">{esc(p["name"])}</text>')
    s.append(f'<text x="66" y="88" font-size="11" fill="{t["hl"]}" letter-spacing="1.2">{esc(p["cat"])}</text>')
    for i, line in enumerate(wrap(p["desc"], 14, bx - 44)):
        s.append(f'<text x="24" y="{120 + i * 20}" font-size="14" fill="{t["muted"]}">{esc(line)}</text>')
    # footer
    s.append(f'<rect x="24" y="{H - 54}" width="{W - 48}" height="1" fill="{t["rule"]}"/>')
    s.append(f'<text x="24" y="{H - 27}" font-size="12.5" fill="{t["muted"]}">{esc("  ·  ".join(p["stack"]))}</text>')
    st = p["status"]
    pw = tw(st, 11) + 26 + (10 if st == "LIVE" else 0)
    px_ = W - 24 - pw
    if st == "LIVE":
        dark_txt = "#06140b" if mode == "dark" else "#ffffff"
        s.append(f'<rect x="{px_:.1f}" y="{H - 41}" width="{pw:.1f}" height="20" rx="10" fill="{t["hl"]}"/>')
        s.append(f'<circle class="led" cx="{px_ + 13:.1f}" cy="{H - 31}" r="3.5" fill="{dark_txt}"/>')
        s.append(f'<text x="{px_ + 22:.1f}" y="{H - 27}" font-size="11" fill="{dark_txt}" letter-spacing="1.2">{st}</text>')
        s.append("<style>" + MOTION % (kf("led", [(0, "opacity:1"), (50, "opacity:.25"), (100, "opacity:1")]) + ".led{animation:led 1.6s ease-in-out infinite}") + "</style>")
    else:
        col = t["hl"] if st in ("CODE", "PAPER") else t["muted"]
        s.append(f'<rect x="{px_:.1f}" y="{H - 41}" width="{pw:.1f}" height="20" rx="10" fill="none" stroke="{col}"/>')
        s.append(f'<text x="{px_ + pw / 2:.1f}" y="{H - 27}" font-size="11" fill="{col}" text-anchor="middle" letter-spacing="1.2">{st}</text>')
    s.append("</svg>")
    return "".join(s)


# ======================= activity monitor =======================
def fetch_calendar(login="nasifsafwan"):
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        import subprocess
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    q = '{"query":"query{user(login:\\"%s\\"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"}' % login
    req = _ur.Request("https://api.github.com/graphql", data=q.encode(), headers={"Authorization": f"bearer {tok}", "User-Agent": "profile-art"})
    data = json.load(_ur.urlopen(req, timeout=30))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], days, weeks


def stats(days, weeks):
    best = max(days, key=lambda d: d[1])
    longest = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur = 0
    seq = list(days)
    if seq and seq[-1][1] == 0:
        seq = seq[:-1]  # today not over yet
    for _, c in reversed(seq):
        if not c:
            break
        cur += 1
    this_week = sum(c for _, c in weeks[-1])
    return dict(best=best, longest=longest, current=cur, week=this_week)


def fmt_date(iso):
    d = _dt.date.fromisoformat(iso)
    return d.strftime("%b %-d")


def activity(t, mode, total, days, weeks):
    W, H = 1000, 330
    st = stats(days, weeks)
    sums = [sum(c for _, c in w) for w in weeks]
    n = len(sums)
    mx = max(max(sums), 1)
    gx, gy, gw, gh = 300, 44, W - 316, H - 96         # graph well
    col_w = (gw - 14) / n
    BLK, GAP = 6, 2                                   # LED block size
    rows = int((gh - 40) // (BLK + GAP))
    L = 11.0
    s, css = [], []
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="{t["frame"]}" stroke="{t["edge"]}"/>')
    s.append(titlebar(t, 1, 1, W - 2, "Activity Monitor"))
    # left readouts
    s.append(f'<rect x="8" y="32" width="{gx - 16}" height="{H - 40}" rx="3" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    s.append(f'<text x="24" y="60" font-size="11" fill="{t["muted"]}" letter-spacing="1.5">CONTRIBUTIONS · LAST 12 MONTHS</text>')
    s.append(f'<text class="p" x="24" y="104" font-size="34" fill="{t["hl"]}">{total:,}</text>')
    cells = [("THIS WEEK", f"{st['week']}", ""), ("BEST DAY", f"{st['best'][1]}", fmt_date(st["best"][0])),
             ("LONGEST STREAK", f"{st['longest']}", "days"), ("CURRENT STREAK", f"{st['current']}", "days")]
    for i, (lab, val, sub) in enumerate(cells):
        cx_, cy_ = 24 + (i % 2) * 134, 140 + (i // 2) * 74
        s.append(f'<rect x="{cx_ - 6}" y="{cy_ - 6}" width="124" height="62" rx="3" fill="{t["frame"]}" stroke="{t["rule"]}"/>')
        s.append(f'<text x="{cx_ + 4}" y="{cy_ + 10}" font-size="10" fill="{t["muted"]}" letter-spacing="1.2">{lab}</text>')
        s.append(f'<text class="p" x="{cx_ + 4}" y="{cy_ + 38}" font-size="18" fill="{t["ink"]}">{val}</text>')
        if sub:
            s.append(f'<text x="{cx_ + 8 + len(val) * 18}" y="{cy_ + 38}" font-size="12" fill="{t["muted"]}">{esc(sub)}</text>')
    # graph well
    s.append(f'<rect x="{gx}" y="32" width="{gw + 8}" height="{H - 40}" rx="3" fill="{t["well"]}" stroke="{t["rule"]}"/>')
    base = gy + gh
    for k in range(rows + 1):
        if k % 4 == 0:
            yy = base - k * (BLK + GAP) + GAP / 2
            s.append(f'<rect x="{gx + 8}" y="{yy:.1f}" width="{gw - 8}" height="1" fill="{t["rule"]}"/>')
    s.append(f'<text x="{gx + gw - 2}" y="{gy + 12}" font-size="10.5" fill="{t["muted"]}" text-anchor="end" letter-spacing="1">PEAK WEEK {mx}</text>')
    lit = t["hl"]
    low = t["g2"]
    off = t["rule"]
    month_seen = set()
    for i, v in enumerate(sums):
        x = gx + 8 + i * col_w
        bwid = max(col_w - 3, 3)
        h_ = 0 if v == 0 else max(1, round((v / mx) ** 0.5 * rows))
        blocks = []
        for k in range(rows):
            y = base - (k + 1) * (BLK + GAP) + GAP
            if k < h_:
                fill = lit if k >= h_ - 1 or k > rows * .6 else low
                blocks.append(f'<rect x="{x:.1f}" y="{y}" width="{bwid:.1f}" height="{BLK}" fill="{fill}"/>')
            elif k < 3:
                blocks.append(f'<rect x="{x:.1f}" y="{y}" width="{bwid:.1f}" height="{BLK}" fill="{off}"/>')
        s.append(f'<g class="c{i}">{"".join(blocks)}</g>')
        # playhead glow over this column + its readout
        s.append(f'<rect class="h{i}" x="{x - 1:.1f}" y="{gy + 18}" width="{bwid + 2:.1f}" height="{gh - 18}" fill="{t["ink"]}" opacity="0"/>')
        wk = weeks[i][0][0]
        label = f"Week of {fmt_date(wk)}  ·  {v}"
        lw = tw(label, 12) + 18
        lx = min(max(x + bwid / 2 - lw / 2, gx + 10), gx + gw - lw - 2)
        s.append(f'<g class="h{i}t" opacity="0"><rect x="{lx:.1f}" y="{gy + 18}" width="{lw:.1f}" height="22" rx="3" fill="{t["frame"]}" stroke="{lit}"/>'
                 f'<text x="{lx + lw / 2:.1f}" y="{gy + 33}" font-size="12" fill="{t["ink"]}" text-anchor="middle">{esc(label)}</text></g>')
        m = _dt.date.fromisoformat(wk).strftime("%b")
        if m not in month_seen and _dt.date.fromisoformat(wk).day <= 7:
            month_seen.add(m)
            s.append(f'<text x="{x:.1f}" y="{base + 20}" font-size="10.5" fill="{t["muted"]}" letter-spacing="1">{m.upper()}</text>')
        # rise on load, then playhead highlight
        d0 = i * 0.022
        start = 1.6
        hd = start + i * (L * 0.85 / n)
        css.append(f".c{i}{{animation:rise .5s cubic-bezier(.2,.8,.3,1) {d0:.3f}s both}}"
                   f".h{i}{{animation:hl {L}s linear {hd:.3f}s infinite}}.h{i}t{{animation:hlt {L}s linear {hd:.3f}s infinite}}")
    # playhead
    s.append(f'<g class="ph"><rect x="{gx + 8}" y="{gy + 40}" width="2" height="{gh - 40}" fill="{lit}"/><rect x="{gx + 5}" y="{base}" width="8" height="5" fill="{lit}"/></g>')
    css.append(kf("rise", [(0, "transform:scaleY(0)"), (100, "transform:scaleY(1)")])
               + "[class^=c]{transform-box:fill-box;transform-origin:50% 100%}"
               + kf("hl", [(0, "opacity:.14"), (1.6, "opacity:.14"), (2.4, "opacity:0"), (100, "opacity:0")])
               + kf("hlt", [(0, "opacity:1"), (1.55, "opacity:1"), (1.6, "opacity:0"), (100, "opacity:0")])
               + kf("ph", [(0, f"transform:translateX(0px);opacity:1"), (85, f"transform:translateX({gw - 8 - col_w:.1f}px);opacity:1"),
                           (86, f"transform:translateX({gw - 8 - col_w:.1f}px);opacity:0"), (100, "transform:translateX(0px);opacity:0")])
               + f".ph{{animation:ph {L}s linear 1.6s infinite both}}")
    s.append(f'<text x="{gx + 8}" y="{H - 20}" font-size="10.5" fill="{t["muted"]}" letter-spacing="1">WEEKLY · EACH COLUMN IS ONE WEEK</text>')
    s.append(f'<text x="{gx + gw}" y="{H - 20}" font-size="10.5" fill="{t["muted"]}" text-anchor="end" letter-spacing="1">UPDATED {_dt.date.today().strftime("%b %-d, %Y").upper()}</text>')
    head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} GitHub contributions in the last 12 months; best day {st["best"][1]} on {fmt_date(st["best"][0])}; longest streak {st["longest"]} days">',
            css_fonts(press_text="0123456789,"), "<style>" + MOTION % "".join(css) + "</style>"]
    return "".join(head + s + ["</svg>"])


def main():
    try:
        cal = fetch_calendar()
    except Exception as e:  # keep the last good chart if the API is unreachable
        print("contributions fetch failed:", e)
        cal = None
    for mode, t in THEMES.items():
        def w(name, svg):
            open(os.path.join(OUT, f"{name}-{mode}.svg"), "w").write(svg)
        w("desktop", banner(t, mode))
        for k, (title, meta) in BARS.items():
            w(f"bar-{k}", bar(t, title, meta))
        for k, (ic, lab) in CHIPS.items():
            w(f"chip-{k}", chip(t, ic, lab))
        w("statusbar", footer(t))
        for p in PROJECTS:
            w(f"app-{p['key']}", project_card(t, mode, p))
        if cal:
            w("monitor", activity(t, mode, *cal))
    print("ok", len(os.listdir(OUT)), "files")


if __name__ == "__main__":
    main()

"""Вёрстка карусели: slides.json (пишет Claude по knowledge/carousel.md) → HTML → PNG 1440×1800 (4:5).
Вёрстка проверяется в браузере: текст не должен вылезать за безопасную зону, иначе шрифт уменьшается."""
import base64
import html
import json
import re
import urllib.parse
from pathlib import Path

from engine import cfg as config, pixel

W, H = 1080, 1350   # вёрстка в CSS-пикселях
SCALE = 4 / 3       # PNG 1440×1800 — максимум, который Instagram хранит для 4:5 (так выкладывает align.go)
FONTS = config.ROOT / "templates" / "fonts"

# ---------- вёрстка ----------

CSS = """
@font-face { font-family: Inter; src: url("%(inter)s"); font-weight: 100 900; }
@font-face { font-family: Caveat; src: url("%(caveat)s"); font-weight: 400 700; }
@font-face { font-family: Pixel; src: url("%(pixel)s"); }
@font-face { font-family: Oswald; src: url("%(oswald)s"); font-weight: 200 700; }
:root { --ink:#0B0B0B; --gray:#8A8A8A; --line:#ECECEC; --soft:#F4F4F5; --accent:%(accent)s; --red:#E5372C; --pen:%(pen)s; --bg:%(bg)s; --k:1; }
* { box-sizing:border-box; margin:0; padding:0; }
html, body { width:%(w)dpx; height:%(h)dpx; overflow:hidden; background:#fff; }
body { font-family:Inter, sans-serif; color:var(--ink); -webkit-font-smoothing:antialiased; font-feature-settings:"cv11"; }
.slide { position:relative; width:100%%; height:100%%; padding:96px 64px 96px; display:flex; flex-direction:column; }
.brand { position:absolute; top:34px; left:0; right:0; text-align:center; font-size:21px; font-weight:600; color:#3A3A3A; }
.brand i { display:inline-block; width:18px; height:18px; border-radius:50%%; background:var(--accent); vertical-align:-3px; margin-right:7px; }
.swipe { position:absolute; bottom:34px; left:0; right:0; text-align:center; font-size:20px; color:#A0A0A0; }
.box { flex:1; display:flex; flex-direction:column; min-height:0; }
h1 { font-size:calc(88px*var(--k)); line-height:1.04; font-weight:800; letter-spacing:-0.025em; text-wrap:balance; }
h1 em, h2 em { font-style:normal; color:var(--accent); }
h2 { font-size:calc(86px*var(--k)); line-height:1.04; font-weight:800; letter-spacing:-0.022em; text-wrap:balance; }
.sub { margin-top:calc(28px*var(--k)); font-size:calc(38px*var(--k)); line-height:1.3; color:var(--gray); font-weight:450; text-wrap:pretty; }
.sub b { color:var(--ink); font-weight:700; }
.punch { margin-top:calc(26px*var(--k)); font-size:calc(38px*var(--k)); line-height:1.25; font-weight:750; }
.visual { display:flex; flex-direction:column; justify-content:center; margin-top:calc(64px*var(--k)); }
.point .box { justify-content:safe center; padding-bottom:40px; }   /* safe: лишнее уходит вниз, где его ловит FIT_JS */
.center { text-align:center; align-items:center; justify-content:safe center; }
.center h2 { font-size:calc(96px*var(--k)); }
/* обложка */
.cover .box { justify-content:flex-end; padding-bottom:60px; }
.cover h1 { font-size:calc(116px*var(--k)); }
.cover .num { font-size:calc(400px*var(--k)); font-weight:850; letter-spacing:-0.05em; line-height:.9; color:var(--accent); margin-bottom:28px; }
/* рукописный слой: пометка ручкой, стрелки, обводки — всё красное, как ручкой по распечатке */
.hand { display:flex; align-items:flex-end; gap:6px; align-self:flex-end; margin:calc(18px*var(--k)) 30px calc(-34px*var(--k)) 0;
  font-family:Caveat; font-size:calc(58px*var(--k)); font-weight:700; line-height:1; color:var(--pen); transform:rotate(-5deg); }
.hand svg { width:96px; height:84px; flex:none; margin-bottom:-36px; }
.hand.up { align-self:center; margin:calc(40px*var(--k)) 0 0; align-items:flex-start; }
.hand.up svg { margin:-44px 0 0; }
.center .hand { align-self:center; }
.cover em, .center em, .cta em { background:url("%(underline)s") left 100%% / 100%% .2em no-repeat; padding-bottom:.08em; }
/* директ */
.chat { position:relative; background:#fff; border:2px solid #E6E6E6; border-radius:44px; transform:rotate(-1.2deg); overflow:visible; }
.chat .top { display:flex; align-items:center; gap:18px; padding:calc(24px*var(--k)) 34px; border-bottom:2px solid #EFEFEF;
  font-size:calc(30px*var(--k)); font-weight:700; }
.chat .top i { width:calc(58px*var(--k)); height:calc(58px*var(--k)); border-radius:50%%; background:#E4E6EB; flex:none; }
.chat .top small { display:block; font-size:calc(22px*var(--k)); font-weight:450; color:var(--gray); }
.chat .feed { display:flex; flex-direction:column; gap:calc(18px*var(--k)); padding:calc(32px*var(--k)) 34px; }
.chat .bar { margin:0 26px calc(26px*var(--k)); padding:calc(20px*var(--k)) 30px; border:2px solid #E6E6E6; border-radius:40px;
  font-size:calc(28px*var(--k)); color:#B0B0B0; }
.msg { max-width:82%%; padding:calc(22px*var(--k)) calc(30px*var(--k)); border-radius:34px; font-size:calc(36px*var(--k)); line-height:1.28; }
.msg.them { align-self:flex-start; background:#EFEFF1; border-bottom-left-radius:8px; }
.msg.me { align-self:flex-end; background:var(--accent); color:#fff; border-bottom-right-radius:8px; }
.badge { position:absolute; top:-30px; right:-14px; padding:12px 24px; border-radius:40px; background:var(--red); color:#fff;
  font-size:calc(32px*var(--k)); font-weight:800; transform:rotate(6deg); }
/* шаги: линия-таймлайн, последний шаг — итоговый, тёмный */
.steps { position:relative; display:flex; flex-direction:column; gap:calc(22px*var(--k)); }
.steps:before { content:""; position:absolute; left:39px; top:40px; bottom:40px; border-left:3px dashed #D6D6D6; }
.step { position:relative; display:flex; gap:28px; align-items:center; font-size:calc(40px*var(--k)); font-weight:600; line-height:1.25; }
.step span { flex:none; width:80px; height:80px; border-radius:50%%; background:#fff; border:3px solid var(--accent); color:var(--accent);
  display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:800; }
.step div { flex:1; padding:calc(28px*var(--k)) 32px; background:var(--soft); border-radius:26px; }
.step:last-child span { background:var(--accent); color:#fff; }
.step:last-child div { background:var(--ink); color:#fff; }
/* цифра в рукописной обводке */
.stat { position:relative; text-align:center; }
.stat .v { position:relative; display:inline-block; padding:0 60px; font-size:calc(300px*var(--k)); font-weight:850; letter-spacing:-0.05em; line-height:1.1; }
.stat .v svg { color:var(--pen); position:absolute; inset:-6%% -4%%; width:108%%; height:112%%; }
.stat .l { margin-top:26px; font-size:calc(40px*var(--k)); color:var(--gray); line-height:1.3; }
/* сравнение: ✕ слева, ✓ справа, стрелка между */
.compare { position:relative; display:grid; grid-template-columns:1fr 1fr; gap:28px; }
.col { padding:calc(44px*var(--k)) 34px; border-radius:30px; background:var(--soft); }
.col.r { background:var(--ink); color:#fff; }
.col h3 { font-size:calc(44px*var(--k)); font-weight:800; margin-bottom:10px; }
.col li { list-style:none; display:flex; gap:14px; font-size:calc(34px*var(--k)); line-height:1.28; margin-top:20px; color:#555; }
.col li:before { content:"✕"; flex:none; color:#B5B5B5; font-weight:700; }
.col.r li { color:#E2E2E2; }
.col.r li:before { content:"✓"; color:color-mix(in srgb, var(--accent) 55%%, white); font-weight:800; }
.compare .vs { position:absolute; left:50%%; top:50%%; width:76px; height:76px; margin:-38px 0 0 -38px; border-radius:50%%;
  background:var(--red); color:#fff; display:flex; align-items:center; justify-content:center; font-size:40px; font-weight:800; }
/* стрелка к решению */
.arrow { display:flex; flex-direction:column; align-items:center; text-align:center; }
.arrow > svg { color:var(--pen); width:150px; height:calc(230px*var(--k)); margin-top:10px; }
.arrow .ico { width:calc(190px*var(--k)); height:calc(190px*var(--k)); margin-top:24px; border-radius:46px; }
.arrow .to { margin-top:26px; font-size:calc(116px*var(--k)); font-weight:850; letter-spacing:-0.035em; line-height:1.02; }
.arrow .note { margin-top:24px; font-size:calc(38px*var(--k)); color:var(--gray); line-height:1.3; max-width:860px; }
/* итог */
.list { margin-top:calc(50px*var(--k)); display:flex; flex-direction:column; }
.list div { display:flex; gap:26px; align-items:baseline; padding:calc(26px*var(--k)) 0; border-bottom:2px solid #EFEFEF;
  font-size:calc(44px*var(--k)); line-height:1.25; font-weight:600; }
.list div:last-child { border:0; }
.list span { flex:none; color:var(--accent); font-weight:800; width:62px; }
.summary .box { justify-content:center; }
/* пиксельный слой: сцены из библиотеки, спидометр, иконки-плитки. Увеличение без сглаживания, размеры кратны сетке
   при выгрузке ×4/3: сцена — целое ×n по её сетке, спидометр 64→768 (×12), плитка 64→384 (×6) */
.scene { display:flex; flex-direction:column; align-items:center; }
.scene img { image-rendering:pixelated; }   /* размер ставится в _visual: целое число точек на пиксель */
.pxlabel { font-family:Pixel; font-size:calc(34px*var(--k)); line-height:1.4; text-align:center; margin-top:18px; }
.gauge { display:flex; flex-direction:column; align-items:center; }
.gauge canvas { width:calc(576px*var(--k)); height:calc(360px*var(--k)); image-rendering:pixelated; }
.gauge .pxlabel { margin:0 0 26px; font-size:calc(52px*var(--k)); }
.tiles { display:flex; justify-content:center; margin-top:26px; }
.tiles canvas { width:calc(288px*var(--k)); height:calc(288px*var(--k)); image-rendering:pixelated; }
.tiles canvas + canvas { margin-left:-48px; margin-top:-54px; }   /* стопкой, без поворота: поворот размывает пиксели */
/* скрин сервиса: реальный кадр сайта/результата в скруглённой рамке, без теней */
.shot { display:flex; flex-direction:column; align-items:center; }
.shot img { max-width:100%%; max-height:calc(700px*var(--k)); border-radius:28px; border:3px solid #ffffff33; }
.shot .cap { margin-top:18px; font-size:calc(28px*var(--k)); color:#8C8C8C; text-align:center; }
/* призыв: шапка Instagram-профиля автора, как на его экране (тёмный режим Instagram) */
.cta .box { justify-content:center; }
.cta h1 { font-size:calc(108px*var(--k)); }
.profile { margin-top:calc(56px*var(--k)); padding:44px 44px 40px; border-radius:44px; background:#0C0F14; color:#F5F5F5;
  border:2px solid #23262D; font-family:-apple-system, "SF Pro Text", Inter, sans-serif; }
.profile .row { display:flex; align-items:center; gap:40px; }
.profile i { width:calc(190px*var(--k)); height:calc(190px*var(--k)); flex:none; border-radius:50%%; background:var(--accent) center/cover;
  color:#fff; display:flex; align-items:center; justify-content:center; font-style:normal; font-size:80px; font-weight:800; }
.profile b { display:block; font-size:44px; font-weight:700; letter-spacing:-0.01em; }
.profile b span { color:#A8A8A8; font-weight:400; margin-left:16px; }
.profile .nm { margin-top:8px; font-size:27px; line-height:1.3; color:#F5F5F5; }
.profile .st { margin-top:18px; display:flex; gap:30px; font-size:27px; color:#F5F5F5; }
.profile .st em { font-style:normal; font-weight:700; }
.profile .bio { margin-top:28px; font-size:27px; line-height:1.45; }
.profile .btns { margin-top:30px; display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.profile u { padding:20px 0; border-radius:18px; background:var(--accent); color:#000; text-align:center;
  text-decoration:none; font-size:28px; font-weight:700; }
.profile u + u { background:#25282E; color:#F5F5F5; }
/* ---------- тёмная тема «кэшью» ---------- */
body.dark { background:%(bg)s; color:#fff; }
html:has(body.dark) { background:%(bg)s; }
.dark .brand { color:#fff; }
.dark .swipe { color:#6B6B6B; }
.dark h1, .dark h2 { font-family:Oswald; font-weight:700; text-transform:uppercase; letter-spacing:0; line-height:1.02; }
.dark h2 { font-size:calc(100px*var(--k)); }
.dark .center h2 { font-size:calc(112px*var(--k)); }
.dark .cover h1 { font-size:calc(136px*var(--k)); }
.dark .cta h1 { font-size:calc(124px*var(--k)); }
.dark .cover .num { font-family:Oswald; font-weight:700; letter-spacing:0; font-size:calc(420px*var(--k)); line-height:.85; }
.dark .sub { color:#C9C9C9; }
.dark .sub b { color:#fff; }
.dark .point .sub, .dark .cta .sub { background:#fff; color:#2A2A2A; padding:calc(30px*var(--k)) 40px; border-radius:40px; font-size:calc(36px*var(--k)); }
.dark .point .sub b, .dark .cta .sub b { color:#000; }
.dark .point.center .sub { text-align:left; }
.dark .punch { color:#fff; }
.dark .chat { border:0; color:#111; }   /* иначе текст переписки наследует белый */
.dark .msg.me { color:#000; }
.dark .steps:before { border-color:#3A3A3A; }
.dark .step span { background:var(--bg); }
.dark .step div { background:#fff; color:#111; }
.dark .step:last-child span { background:var(--accent); color:#000; }
.dark em { background:none; padding:0; }   /* узкие строки — подчёркивание наезжает, акцент и так жёлтый */
.dark .step:last-child div { background:var(--accent); color:#000; }
.dark .stat .v { color:#fff; }
.dark .stat .l { color:#C9C9C9; }
.dark .col { background:#fff; color:#111; }
.dark .col li { color:#444; }
.dark .col.r { background:var(--accent); color:#000; }
.dark .col.r li { color:#222; }
.dark .col.r li:before { color:#000; }
.dark .arrow .to { color:#fff; font-family:Oswald; text-transform:uppercase; font-weight:700; letter-spacing:0; }
.dark .arrow .note { color:#C9C9C9; }
.dark .list div { border-color:#262626; }
.dark .scene, .dark .gauge { background:#fff; border-radius:44px; padding:44px 50px; align-self:center; }
.dark .scene .pxlabel { color:#111; }
.dark .gauge .pxlabel { color:#000 !important; background:var(--accent); padding:12px 22px; border-radius:14px; }
"""

ARROW = ('<svg viewBox="0 0 120 200" fill="none" stroke="currentColor" stroke-width="9" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M62 8 C 54 60, 66 110, 58 182"/><path d="M26 146 L58 184 L94 142"/></svg>')
# изогнутые стрелки рядом с рукописной пометкой: вниз-влево (на визуал под ней) и вверх (на текст над ней)
HAND_DOWN = ('<svg viewBox="0 0 96 84" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M86 10 C 60 8, 28 26, 18 72"/><path d="M6 54 L18 74 L34 58"/></svg>')
HAND_UP = ('<svg viewBox="0 0 96 84" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">'
           '<path d="M86 76 C 56 78, 26 58, 20 12"/><path d="M6 28 L20 10 L36 26"/></svg>')
OVAL = ('<svg viewBox="0 0 400 200" preserveAspectRatio="none" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round">'
        '<path d="M210 14 C 90 6, 14 44, 16 104 C 18 166, 120 194, 222 188 C 330 182, 392 140, 384 88 C 376 36, 300 10, 170 22"/></svg>')
underline = lambda color: "data:image/svg+xml," + urllib.parse.quote(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 20" preserveAspectRatio="none">'
    f'<path d="M4 14 C 80 6, 180 4, 296 10" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/></svg>')
# темы: light — чистый белый стиль @align.go; dark — структура гайдов «кэшью» (тёмный фон, узкие капс-заголовки,
# текст в белых карточках), цвета из config.json: accent / bg. Перо — пометки, стрелки, обводки.
THEMES = {"light": {"pen": "#E5372C", "bg": "#FFFFFF"},
          "dark": {"pen": None, "bg": None}}   # None — перо цвета акцента, фон из config
ICONS = config.ROOT / "templates" / "icons"
PHOTOS = config.ROOT / "templates" / "photos"   # avatar.jpg — фото автора для карточки профиля


def _t(s, em="em"):
    """Текст из JSON → HTML: **слово** → акцент (em в заголовке, b в тексте)."""
    return re.sub(r"\*\*(.+?)\*\*", rf"<{em}>\1</{em}>", html.escape(s or ""))


def _icon(names):
    """Иконки сервисов пиксельными плитками с объёмом (рисует PX_JS). names — строка или список, до 2."""
    names = [names] if isinstance(names, str) else (names or [])
    files = [ICONS / f"{n.strip().lower()}.svg" for n in names if n][:2]
    # data: вместо file:// — иначе canvas «испорчен» и PX_JS не может прочитать пиксели
    # на плитку идёт только знак (icons/glyph/<имя>.svg), если он есть отдельно от фона логотипа
    glyph = lambda f: f.parent / "glyph" / f.name if (f.parent / "glyph" / f.name).exists() else f
    tiles = "".join(f'<canvas class="px-icon" data-src="data:image/svg+xml;base64,{base64.b64encode(glyph(f).read_bytes()).decode()}"'
                    f' data-tile="{TILE.get(f.stem, "")}"></canvas>' for f in files if f.exists())
    return f'<div class="tiles">{tiles}</div>' if tiles else ""


# цвет плитки; знак на ней становится белым (у lovable — свой цветной знак на белой плитке)
TILE = {"claude": "#D97757", "telegram": "#2AABEE", "instagram": "#1E1E1E", "vercel": "#1E1E1E", "v0": "#1E1E1E",
        "bolt": "#1E1E1E", "lovable": "#FFFFFF", "google": "#FFFFFF"}
GAUGE = {"легко": (1, "#3DA63F"), "средне": (2, "#E8A317"), "сложно": (3, "#E5372C")}


def _hand(note, up=False):
    """Рукописная пометка с изогнутой стрелкой: вниз — на визуал под ней, вверх — на текст над ней."""
    if not note:
        return ""
    return (f'<div class="hand up">{HAND_UP}{html.escape(note)}</div>' if up
            else f'<div class="hand">{html.escape(note)}{HAND_DOWN}</div>')


def _visual(v):
    k = (v or {}).get("kind")
    if k == "chat":
        return ('<div class="chat">' + (f'<div class="badge">{html.escape(v["badge"])}</div>' if v.get("badge") else "")
                + f'<div class="top"><i></i><div>{html.escape(v.get("who") or "Подписчик")}<small>Директ</small></div></div>'
                + '<div class="feed">' + "".join(
                    f'<div class="msg {"me" if m.get("from") == "me" else "them"}">{_t(m.get("text"), "b")}</div>'
                    for m in v.get("messages", [])[:4]) + '</div><div class="bar">Сообщение…</div></div>')
    if k == "steps":
        return '<div class="steps">' + "".join(
            f'<div class="step"><span>{i}</span><div>{_t(s, "b")}</div></div>'
            for i, s in enumerate(v.get("items", [])[:5], 1)) + "</div>"
    if k == "stat":
        return (f'<div class="stat"><div class="v">{OVAL}{_t(v.get("value"))}</div>'
                f'<div class="l">{_t(v.get("label"), "b")}</div></div>')
    if k == "compare":
        col = lambda c, cls: (f'<div class="col {cls}"><h3>{_t(c.get("title"))}</h3><ul>'
                              + "".join(f"<li>{_t(x, 'b')}</li>" for x in c.get("items", [])[:3]) + "</ul></div>")
        return (f'<div class="compare">{col(v.get("left") or {}, "")}{col(v.get("right") or {}, "r")}'
                '<div class="vs">→</div></div>')
    if k == "scene":
        f = pixel.PIXEL_DIR / f"{v.get('id')}.png"
        if not f.exists():
            return ""
        from PIL import Image
        w, h = Image.open(f).size
        n = max(1, min(6, int(1000 / max(w, h * 1.25))))  # во сколько точек выгрузки один пиксель сцены — целое
        return (f'<div class="scene"><img src="{f.as_uri()}" style="width:calc({w * n * 0.75}px*var(--k));'
                f'height:calc({h * n * 0.75}px*var(--k))">'
                + (f'<div class="pxlabel">{html.escape(v["label"])}</div>' if v.get("label") else "") + "</div>")
    if k == "gauge":
        level, color = GAUGE.get((v.get("level") or "").lower(), (2, "#E8A317"))
        return (f'<div class="gauge"><div class="pxlabel" style="color:{color}">{html.escape((v.get("level") or "").upper())}</div>'
                f'<canvas class="px-gauge" data-level="{level}" data-color="{color}"></canvas></div>')
    if k == "shot":   # src — путь к PNG/JPG (от корня проекта или абсолютный), только настоящие скрины
        f = Path(v.get("src") or "")
        f = f if f.is_absolute() else config.ROOT / f
        return (f'<div class="shot"><img src="{f.as_uri()}">' + (f'<div class="cap">{_t(v.get("cap"), "b")}</div>'
                if v.get("cap") else "") + "</div>") if f.exists() else ""
    if k == "arrow":
        return (f'<div class="arrow">{ARROW}{_icon(v.get("icon"))}<div class="to">{_t(v.get("to"))}</div>'
                + (f'<div class="note">{_t(v.get("note"), "b")}</div>' if v.get("note") else "") + "</div>")
    return ""


def _avatar():
    f = next((p for p in PHOTOS.glob("avatar.*")), None) if PHOTOS.exists() else None
    return f'<i style="background-image:url({f.as_uri()})"></i>' if f else f"<i>{html.escape((config.CAROUSEL_HANDLE or '?')[:1].upper())}</i>"


def _profile(handle):
    """Шапка профиля Instagram (данные — config.json → profile)."""
    pr = config.CAROUSEL_PROFILE
    bio = "".join(f"<div>{html.escape(x)}</div>" for x in pr["bio"])
    return (f'<div class="profile"><div class="row">{_avatar()}<div><b>{html.escape(handle)}<span>···</span></b>'
            f'<div class="nm">{html.escape(pr["name"])}</div>'
            f'<div class="st"><span><em>{pr["posts"]}</em> публикаций</span><span><em>{pr["followers"]}</em> подписчиков</span>'
            f'<span><em>{pr["following"]}</em> подписок</span></div></div></div>'
            f'<div class="bio">{bio}</div><div class="btns"><u>Подписаться</u><u>Сообщение</u></div></div>')


def slide_html(s, handle, last, accent=None, theme=None, bg=None):
    t, note = s.get("type"), s.get("note")
    if t == "cover":
        m = re.match(r"\s*(\d+)\s+(.+)", s.get("title") or "", re.S)  # «5 мест…» → 5 крупно, дальше заголовок
        body = (_hand(note) + f'<div class="num">{m[1]}</div>' if m else "") + \
               f'<h1>{_t(m[2] if m else s.get("title"))}</h1><p class="sub">{_t(s.get("sub"), "b")}</p>' + \
               ("" if m else _hand(note, up=True))
    elif t == "summary":
        body = f'<h2>{_t(s.get("title"))}</h2><div class="list">' + "".join(
            f"<div><span>{i:02d}</span>{_t(x, 'b')}</div>" for i, x in enumerate(s.get("items", [])[:7], 1)) + "</div>" + \
            _hand(note, up=True)
    elif t == "cta":
        body = (f'<h1>{_t(s.get("title"))}</h1><p class="sub">{_t(s.get("text"), "b")}</p>' + _hand(note) +
                _profile(handle))
    else:
        vis = _visual(s.get("visual"))
        head = (f'<h2>{_t(s.get("title"))}</h2>' + (f'<p class="sub">{_t(s.get("text"), "b")}</p>' if s.get("text") else "")
                + (f'<p class="punch">{_t(s.get("punch"))}</p>' if s.get("punch") else ""))
        if not vis:
            t = "point center"
            body = head + _hand(note, up=True)
        elif (s.get("visual") or {}).get("kind") == "arrow":
            t = "point center"
            body = f'<h2>{_t(s.get("title"))}</h2><div class="visual">{vis}</div>'
        else:
            body = head + _hand(note) + f'<div class="visual">{vis}</div>'
    cls = t.split()[0] + (" center" if "center" in t else "")
    box_cls = "box center" if "center" in t else "box"
    theme = theme or config.CAROUSEL_THEME
    th = THEMES[theme]
    accent = accent or config.CAROUSEL_ACCENT
    pen = th["pen"] or accent
    css = CSS % {"accent": accent, "pen": pen, "bg": bg or th["bg"] or config.CAROUSEL_BG, "oswald": (FONTS / "Oswald.ttf").as_uri(), "inter": (FONTS / "InterVariable.ttf").as_uri(), "caveat": (FONTS / "Caveat.ttf").as_uri(),
                 "pixel": (FONTS / "PressStart2P.ttf").as_uri(), "underline": underline(pen), "w": W, "h": H}
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>'
            f'<body class="{theme}"><div class="slide {cls}"><div class="brand"><i></i>{html.escape(handle)}</div>'
            f'<div class="{box_cls}">{body}</div>'
            + ("" if last else '<div class="swipe">листай дальше →</div>') + f"</div><script>{PX_JS}</script></body></html>")


# Пиксели рисуются на маленьком canvas (иконка 30×30, спидометр 64×40) без полупрозрачных краёв,
# а CSS растягивает его с image-rendering: pixelated — так получаются ровные квадратные пиксели.
PX_JS = """
// края без полупрозрачности; с палитрой — каждая точка к ближайшему цвету (canvas сглаживает линии полутонами)
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const crisp = (c, pal) => { const x = c.getContext('2d'), d = x.getImageData(0, 0, c.width, c.height), P = (pal || []).map(hex);
  for (let i = 0; i < d.data.length; i += 4) {
    d.data[i + 3] = d.data[i + 3] > 110 ? 255 : 0;
    if (!P.length || !d.data[i + 3]) continue;
    let best = P[0], bd = 1e9;
    for (const q of P) { const dd = (q[0] - d.data[i]) ** 2 + (q[1] - d.data[i + 1]) ** 2 + (q[2] - d.data[i + 2]) ** 2; if (dd < bd) { bd = dd; best = q; } }
    d.data[i] = best[0]; d.data[i + 1] = best[1]; d.data[i + 2] = best[2];
  }
  x.putImageData(d, 0, 0); };
window.pxReady = Promise.all([...document.querySelectorAll('canvas.px-icon')].map(c => new Promise(ok => {
  const img = new Image(); img.onload = () => {
    // сетка 64: белая обводка-наклейка, тёмный контур, грань-скос снизу, плитка, белый логотип (как у align.go)
    c.width = 64; c.height = 64; const x = c.getContext('2d'), t = c.dataset.tile;
    const rr = (dx, dy, w, h, r, col) => { x.beginPath(); x.roundRect(dx, dy, w, h, r); x.fillStyle = col; x.fill(); };
    const shade = h => '#' + hex(h).map(v => Math.round(v * 0.72).toString(16).padStart(2, '0')).join('');
    rr(0, 0, 64, 64, 15, '#FFFFFF');
    rr(2, 2, 60, 60, 13, '#1E1E1E');
    if (t) {
      rr(4, 4, 56, 56, 11, shade(t)); rr(4, 4, 56, 52, 11, t);
      x.filter = t === '#FFFFFF' ? 'none' : 'brightness(0) invert(1)'; x.drawImage(img, 14, 12, 36, 36);
    } else {
      x.save(); x.beginPath(); x.roundRect(4, 4, 56, 56, 11); x.clip(); x.drawImage(img, 4, 4, 56, 56); x.restore();
    }
    crisp(c, t && t !== '#FFFFFF' ? [t, shade(t), '#1E1E1E', '#FFFFFF'] : null); ok(); };
  img.onerror = ok; img.src = c.dataset.src; })));
// спидометр считается попиксельно: дуга-контур, серая шкала, цветная часть по уровню, стрелка — без сглаживания вообще
for (const c of document.querySelectorAll('canvas.px-gauge')) {
  c.width = 64; c.height = 40; const x = c.getContext('2d'), cx = 31.5, cy = 34.5, lv = +c.dataset.level;
  const ink = '#2B2B2B', na = Math.PI * (1 - (lv / 3 - 1 / 6));   // угол стрелки: 0 — вправо, π — влево
  const put = (px, py, col) => { x.fillStyle = col; x.fillRect(px, py, 1, 1); };
  for (let py = 0; py < 40; py++) for (let px = 0; px < 64; px++) {
    const dx = px - cx, dy = cy - py, d = Math.hypot(dx, dy), a = Math.atan2(dy, dx);
    if (dy < -1.5) continue;
    if (d >= 18 && d <= 30) {
      const inner = d > 19.5 && d < 28.5 && dy > 0.5;
      put(px, py, !inner ? ink : (a >= Math.PI * (1 - lv / 3) ? c.dataset.color : '#D9D9D9'));
    }
    const t = dx * Math.cos(na) + dy * Math.sin(na), off = Math.abs(-dx * Math.sin(na) + dy * Math.cos(na));
    if (t > 0 && t < 17 && off < 1.3) put(px, py, ink);
  }
  x.fillStyle = ink; x.fillRect(28, 31, 7, 7);
}
"""


# Уменьшает шрифт (--k), пока содержимое не влезет в слайд; возвращает итог проверки безопасной зоны.
FIT_JS = """() => {
  const box = document.querySelector('.box'), root = document.documentElement;
  const over = () => box.scrollHeight > box.clientHeight + 1 ||
    [...document.querySelectorAll('.visual > *')].some(e => e.scrollHeight > e.parentElement.clientHeight + 1);
  let k = 1;
  while (over() && k > 0.72) { k -= 0.04; root.style.setProperty('--k', k.toFixed(2)); }
  const bad = [...document.querySelectorAll('h1,h2,p,.msg,.step,.col,.to,.note,.list div,.v,.l,.hand,.profile,.badge')].filter(e => {
    const r = e.getBoundingClientRect();
    return r.width && (r.left < 34 || r.right > 1046 || r.top < 70 || r.bottom > 1290);
  }).map(e => e.textContent.slice(0, 40));
  return {k: +k.toFixed(2), overflow: over(), outside: bad};
}"""


def render(pw, slides, out_dir, handle=None, accent=None, theme=None, bg=None):
    """slides → out_dir/slide_NN.png (+ .html). → список предупреждений."""
    handle = handle or config.CAROUSEL_HANDLE
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings = []
    try:
        browser = pw.chromium.launch(channel="chrome", headless=True)
    except Exception:   # нет Google Chrome — встроенный chromium (patchright install chromium)
        browser = pw.chromium.launch(headless=True)
    try:
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        for i, s in enumerate(slides, 1):
            f = out_dir / f"slide_{i:02d}.html"
            f.write_text(slide_html(s, handle, i == len(slides), accent, theme, bg), encoding="utf-8")
            page.goto(f.as_uri())
            page.evaluate("document.fonts.ready")
            page.evaluate("window.pxReady")
            r = page.evaluate(FIT_JS)
            if r["overflow"] or r["outside"]:
                warnings.append(f"слайд {i}: " + ("не влез" if r["overflow"] else "") +
                                (f" за краем: {r['outside']}" if r["outside"] else ""))
            elif r["k"] < 1:
                warnings.append(f"слайд {i}: шрифт уменьшен до {int(r['k'] * 100)}%")
            page.screenshot(path=str(out_dir / f"slide_{i:02d}.png"), clip={"x": 0, "y": 0, "width": W, "height": H})
    finally:
        browser.close()
    return warnings

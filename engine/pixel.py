"""Пиксельные сцены для каруселей: генерация в веб-Gemini (подписка пользователя, без API-ключа) → чистка → templates/pixel/<id>.png.
Gemini открывается в отдельном Chrome (профиль ~/.chrome-gemini-profile, порт 9222), основной Chrome не трогается.
Чистка: белый фон → прозрачный, обрезка по объекту, пиксели по родной сетке Gemini (~256 по ширине, CSS увеличивает без сглаживания)."""
import base64
import subprocess
import time
import urllib.request
from pathlib import Path

from PIL import Image

from engine import cfg as config

PIXEL_DIR = config.ROOT / "templates" / "pixel"
CDP = "http://localhost:9222"
PROFILE = Path.home() / ".chrome-gemini-profile"
CHROME = config.CHROME
NATIVE = 256        # Gemini рисует пиксель-арт на сетке ≈256 по ширине (пиксель ≈4 точки при 1024)
COLORS = 24         # палитра, как у 16-битных игр

STYLE = ("Pixel art illustration in retro 16-bit video game style. Chunky clearly visible square pixels, crisp dark "
         "outlines, flat cel shading with 2-3 tones per color, limited palette, warm natural colors. One isolated object "
         "centered on a pure white background, square 1:1 image, the whole object fully inside the frame with white margin around it, no ground shadow, no text, no letters, no border, no frame. Subject: ")


def _cdp_up():
    try:
        urllib.request.urlopen(CDP + "/json/version", timeout=2)
        return True
    except Exception:
        return False


def ensure_chrome():
    if _cdp_up():
        return
    subprocess.Popen([CHROME, "--remote-debugging-port=9222", f"--user-data-dir={PROFILE}", "--no-first-run",
                      "https://gemini.google.com/app"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        if _cdp_up():
            return
    raise RuntimeError("Chrome с Gemini не запустился")


FIND_IMG = """() => {
  const imgs = [...document.querySelectorAll('img')].filter(i => i.naturalWidth >= 512 && i.naturalHeight >= 512)
    .filter(i => !/profile|avatar|gstatic\\.com\\/lamda/i.test(i.src));
  return imgs.length ? imgs[imgs.length - 1].src : null;
}"""
CANVAS_IMG = """() => {
  const imgs = [...document.querySelectorAll('img')].filter(i => i.naturalWidth >= 512 && i.naturalHeight >= 512)
    .filter(i => !/profile|avatar/i.test(i.src));
  const img = imgs[imgs.length - 1], c = document.createElement('canvas');
  c.width = img.naturalWidth; c.height = img.naturalHeight; c.getContext('2d').drawImage(img, 0, 0);
  return c.toDataURL('image/png');
}"""


def generate(pw, subject, out):
    """Одна картинка в новом чате Gemini → out (PNG как есть)."""
    browser = pw.chromium.connect_over_cdp(CDP)
    ctx = browser.contexts[0]
    page = next((p for p in ctx.pages if "gemini.google" in p.url), None) or ctx.new_page()
    page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    if "accounts.google" in page.url or page.get_by_text("Sign in to connect").count() \
            or page.get_by_text("Войдите", exact=False).count():
        raise RuntimeError("Gemini не залогинен: войди в окне Chrome (профиль ~/.chrome-gemini-profile) и запусти ещё раз")
    box = page.locator('div[contenteditable="true"]').first
    box.wait_for(state="visible", timeout=20000)
    box.click()
    box.fill("Generate an image. " + STYLE + subject)
    page.wait_for_timeout(400)
    page.keyboard.press("Enter")
    src, t0 = None, time.time()
    while time.time() - t0 < 180:
        page.wait_for_timeout(3000)
        src = page.evaluate(FIND_IMG)
        if src:
            break
    if not src:
        page.screenshot(path=str(out.with_suffix(".fail.png")))
        raise RuntimeError("картинка не появилась за 3 мин")
    for attempt in range(8):  # blob: живёт недолго и меняется на googleusercontent — каждый раз берём свежий src
        if attempt:
            page.wait_for_timeout(4000)
        cur = page.evaluate(FIND_IMG) or src
        try:
            if cur.startswith("blob:"):
                out.write_bytes(base64.b64decode(page.evaluate(CANVAS_IMG).split(",", 1)[1]))
                return out
            for url in (cur.split("=s")[0] + "=s2048", cur):
                r = ctx.request.get(url)
                if r.ok:
                    out.write_bytes(r.body())
                    return out
        except Exception:
            pass
    raise RuntimeError("не удалось скачать картинку")


def clean(src, out):
    """Белый фон (связный с краями) → прозрачный, обрезка, родная сетка Gemini (≈256 по ширине), палитра COLORS.
    Фон ищется на полном разрешении, светлая кайма по краю объекта срезается."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = im.load()
    near_white = lambda c: min(c) > 228 and max(c) - min(c) < 22
    bg = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < w and 0 <= y < h) or bg[y * w + x] or not near_white(px[x, y]):
            continue
        bg[y * w + x] = 1
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    alpha = Image.frombytes("L", (w, h), bytes(0 if v else 255 for v in bg))
    cell = max(1, round(w / NATIVE))                 # сторона «пикселя» Gemini в точках
    gw, gh = w // cell, h // cell
    rgb = im.resize((gw, gh), Image.BOX).quantize(COLORS, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    a = alpha.resize((gw, gh), Image.BOX).point(lambda v: 255 if v > 140 else 0)
    rgb.putalpha(a)
    d = rgb.load()
    for _ in range(2):  # кайма: светлые точки на границе с прозрачным
        edge = [(x, y) for y in range(gh) for x in range(gw) if d[x, y][3] and min(d[x, y][:3]) > 205 and any(
            not (0 <= x + dx < gw and 0 <= y + dy < gh) or not d[x + dx, y + dy][3]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in edge:
            d[x, y] = (255, 255, 255, 0)
    rgb.crop(rgb.getbbox()).save(out)
    return out


def library():
    import json
    return json.loads((PIXEL_DIR / "library.json").read_text(encoding="utf-8"))


def ready():
    """id сцен, у которых уже есть готовая картинка."""
    return sorted(k for k in library() if (PIXEL_DIR / f"{k}.png").exists())


def build(pw, only=None, log=print):
    """Догенерировать недостающие сцены библиотеки по одной (Gemini медленный, компьютер не грузим)."""
    ensure_chrome()
    (PIXEL_DIR / "raw").mkdir(parents=True, exist_ok=True)
    todo = [k for k in library() if (only is None or k in only) and not (PIXEL_DIR / f"{k}.png").exists()]
    fails = 0
    for i, k in enumerate(todo, 1):
        try:
            raw = generate(pw, library()[k]["en"], PIXEL_DIR / "raw" / f"{k}.png")
            clean(raw, PIXEL_DIR / f"{k}.png")
            log(f"{i}/{len(todo)} {k}: готово")
            fails = 0
        except Exception as e:
            log(f"{i}/{len(todo)} {k}: {e}")
            fails += 1
            if "не залогинен" in str(e) or fails >= 3:  # 3 подряд — скорее всего дневной лимит Gemini
                log("Остановился: 3 ошибки подряд или нет входа. Запусти позже, готовые сцены не пересоздаются.")
                break
    return ready()

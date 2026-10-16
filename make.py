"""Команды системы каруселей (запускать из папки системы через .venv/bin/python make.py …):
    render <папка или slides.json> [--theme dark|light] [--accent #hex] [--bg #hex]
                                     — сверстать slides.json → slide_NN.png + contact_sheet.png (+ предупреждения о вёрстке);
                                       флаги — примерить стиль, не меняя config.json
    scenes                           — готовые пиксельные сцены: id — когда ставить
    icons                            — иконки сервисов для визуала arrow
    shot <url> <файл.png> [css]      — настоящий скрин сайта через Chrome (масштаб 2); css — снять только этот блок
    pixels [id ...]                  — догенерировать пиксельные сцены из templates/pixel/library.json через веб-Gemini
    gemini                           — открыть отдельный Chrome с Gemini, чтобы один раз войти в Google
    check                            — проверить, что всё установлено"""
import json
import sys
from pathlib import Path

from engine import cfg


def sheet(out_dir):
    """Все слайды одной картинкой — смотреть карусель целиком."""
    from PIL import Image
    files = sorted(out_dir.glob("slide_*.png"))
    if not files:
        return None
    w, h, cols, gap = 360, 450, 4, 16
    rows = (len(files) + cols - 1) // cols
    im = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), "#D9D9D9")
    for i, f in enumerate(files):
        im.paste(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS),
                 (gap + (i % cols) * (w + gap), gap + (i // cols) * (h + gap)))
    p = out_dir / "contact_sheet.png"
    im.save(p)
    return p


def render(arg, theme=None, accent=None, bg=None):
    from patchright.sync_api import sync_playwright
    from engine import carousel
    f = Path(arg).resolve()
    f = f / "slides.json" if f.is_dir() else f
    slides = json.loads(f.read_text(encoding="utf-8"))
    slides = slides["slides"] if isinstance(slides, dict) else slides
    with sync_playwright() as pw:
        warn = carousel.render(pw, slides, f.parent, theme=theme, accent=accent, bg=bg)
    print(f"{len(slides)} слайдов → {f.parent}")
    print("Сводка:", sheet(f.parent))
    print("Вёрстка в порядке" if not warn else "Проверь:\n" + "\n".join(warn))


def shot(url, out, selector=None):
    from patchright.sync_api import sync_playwright
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch(channel="chrome", headless=True)
        except Exception:
            b = pw.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        (page.locator(selector).first if selector else page).screenshot(path=str(out))
        b.close()
    print(out)


def check():
    import importlib.util
    ok = True
    for mod in ("patchright", "PIL"):
        if not importlib.util.find_spec(mod):
            print("нет модуля", mod); ok = False
    for f in ("Oswald.ttf", "InterVariable.ttf", "Caveat.ttf", "PressStart2P.ttf"):
        if not (cfg.ROOT / "templates" / "fonts" / f).exists():
            print("нет шрифта", f); ok = False
    print("Google Chrome:", "есть" if Path(cfg.CHROME).exists() else "НЕТ (рендер пойдёт через встроенный chromium)")
    print("Аватарка:", "есть" if list((cfg.ROOT / "templates" / "photos").glob("avatar.*")) else "нет — на карточке профиля будет буква")
    print("Ник:", cfg.CAROUSEL_HANDLE, "| тема:", cfg.CAROUSEL_THEME, "| акцент:", cfg.CAROUSEL_ACCENT)
    print("Всё на месте" if ok else "Есть проблемы — см. выше")


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else ""
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    if cmd == "render" and len(a) > 1:
        render(a[1], opt("--theme"), opt("--accent"), opt("--bg"))
    elif cmd == "scenes":
        from engine import pixel
        lib = pixel.library()
        for k in pixel.ready():
            print(f"{k}: {lib[k]['ru']}")
    elif cmd == "icons":
        print(", ".join(sorted(f.stem for f in (cfg.ROOT / "templates" / "icons").glob("*.svg"))))
    elif cmd == "shot" and len(a) > 2:
        shot(a[1], a[2], a[3] if len(a) > 3 else None)
    elif cmd == "gemini":
        from engine import pixel
        pixel.ensure_chrome()
        print("Открыл Chrome с Gemini. Войди в Google в этом окне, потом можно генерировать сцены.")
    elif cmd == "pixels":
        from patchright.sync_api import sync_playwright
        from engine import pixel
        with sync_playwright() as pw:
            print("Готово сцен:", len(pixel.build(pw, only=a[1:] or None)), "из", len(pixel.library()))
    elif cmd == "check":
        check()
    else:
        print(__doc__)

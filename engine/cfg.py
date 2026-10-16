"""Настройки автора из config.json (заполняет Claude по анкете из SETUP.md)."""
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_c = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

CAROUSEL_HANDLE = _c.get("handle") or "your.nick"
CAROUSEL_THEME = _c.get("theme") or "dark"      # dark — тёмный фон, капс-заголовки, текст в белых карточках; light — белый стиль
CAROUSEL_ACCENT = _c.get("accent") or "#FF7A1F"
CAROUSEL_BG = _c.get("bg") or "#0E0B09"
CAROUSEL_PROFILE = {"name": "", "posts": 0, "followers": 0, "following": 0, "bio": [], **(_c.get("profile") or {})}
OUTPUT = ROOT / "output"

CHROME = {
    "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}.get(platform.system(), "google-chrome")

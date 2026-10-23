"""Builder 101: reads a build from a deepwoken.co builder link (the build's name and the talents in it),
and spots those talents in text read off your screen (the talent cards you're offered on level up)."""
import difflib
import html
import re
import urllib.request

BUILDER_URL = re.compile(r"^https?://(www\.)?deepwoken\.co/builder\?id=([A-Za-z0-9_-]+)")


def fetch(url, timeout=15):
    """{'name': str, 'talents': [str]} for a deepwoken.co builder link."""
    url = url.strip()
    if not BUILDER_URL.match(url):
        raise ValueError("paste a link like https://deepwoken.co/builder?id=...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ElgansitoDemolisherMacro)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        page = r.read().decode("utf-8", "replace")
    return parse(page)


def parse(page):
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    name = html.unescape(title.group(1)).replace("- Deepwoken Builder", "").strip() if title else "Build"
    talents = []
    # Each talent on the page is an element with data-talent-name; picked ones have aria-pressed="true".
    for m in re.finditer(r'<[^>]*data-talent-name="([^"]+)"[^>]*>', page):
        if 'aria-pressed="true"' in m.group(0):
            t = html.unescape(m.group(1)).strip()
            if t and t not in talents:
                talents.append(t)
    if not talents:
        raise ValueError("no talents found in that build (is it public?)")
    return {"name": name, "talents": talents}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def find_talents(screen_text, talents, threshold=0.86):
    """Talents (from the build) whose names appear in OCR text, allowing small OCR mistakes."""
    words = norm(screen_text).split()
    found = []
    for t in talents:
        tw = norm(t).split()
        if not tw:
            continue
        n = len(tw)
        target = " ".join(tw)
        for i in range(0, max(len(words) - n + 1, 0)):
            window = " ".join(words[i:i + n])
            if window == target or difflib.SequenceMatcher(None, window, target).ratio() >= threshold:
                found.append(t)
                break
    return found

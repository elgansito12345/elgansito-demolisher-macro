"""Finds the row of cards Deepwoken offers on level up (talents, mantras) and reads each card's title.

Only a row of two or more cards side by side counts, so a single card (the tooltip you get hovering a
talent in your inventory, or the talent list itself) never triggers anything. Defaults are for a
1920x1080 screen: the cards sit in the middle, titles on a light banner at the top of each card and
the description on light parchment lower down.
"""
import cv2

import servername

DEFAULT_AREA = [380, 300, 1160, 340]   # x, y, w, h around the whole card row
TITLE_BAND = (0.09, 0.23)               # where the title banners are, as a share of the area's height
BODY_BAND = (0.55, 0.85)                # where the description parchment is


def find_cards(img):
    """[(x0, x1)] for each card in the area (empty unless there are at least two)."""
    h, w = img.shape[:2]
    band = img[int(h * BODY_BAND[0]):int(h * BODY_BAND[1])]
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
    parchment = (hsv[..., 2] > 195) & (hsv[..., 1] < 45)
    cols = parchment.mean(axis=0) > 0.55
    runs, start = [], None
    for x, on in enumerate(list(cols) + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            runs.append((start, x))
            start = None
    cards = [(a, b) for a, b in runs if 0.09 * w <= b - a <= 0.24 * w]
    return cards if len(cards) >= 2 else []


def read_titles(img, cards):
    """[(title text, (x0, x1))] for each card; dark text on a light banner, so no inverting."""
    h = img.shape[0]
    out = []
    for x0, x1 in cards:
        pad = int((x1 - x0) * 0.08)
        crop = img[int(h * TITLE_BAND[0]):int(h * TITLE_BAND[1]), max(x0 - pad, 0):x1 + pad]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        try:
            text = servername.run_ocr(gray).strip()
        except Exception:
            text = ""
        out.append((text, (x0, x1)))
    return out


def read_row(img):
    """Cards in the area as [(title, (x0, x1))], or [] when no card row is showing."""
    cards = find_cards(img)
    return read_titles(img, cards) if cards else []

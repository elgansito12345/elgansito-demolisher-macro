"""Standalone always-on-top overlays you can drag anywhere on screen."""
import math
import time
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QWidget

import combat

READY = QColor("#34d399")
TEXT = QColor("#e6e8ee")
MUTED = QColor("#8b93a5")
LANDED = QColor("#fde047")


def hp_color(frac):
    if frac > 0.60:
        return QColor("#34d399")
    if frac > 0.35:
        return QColor("#fbbf24")
    if frac > 0.15:
        return QColor("#fb923c")
    return QColor("#ef4444")


def widget_catalog(cfg):
    """(id, title, description) for every overlay that can be placed."""
    items = [
        ("status", "Status pill", "Shows whether macros are on and the game is focused."),
        ("macros", "Macro list", "Your macros, their hotkeys, and which one is running."),
        ("party", "Party HP", "Your HP and your friends' HP as bars, shared between Elgansito Demolisher Macro users."),
    ]
    for cd in cfg.get("cooldowns", []):
        items.append((f"cooldown:{cd['name']}", f"{cd['name']} bar",
                      f"Live {cd['name'].lower()} cooldown bar. Flashes when it lands."))
    return items


class Overlay(QWidget):
    def __init__(self, controller, wid, w, h):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.controller = controller
        self.wid = wid
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle(wid)
        self.resize(w, h)
        self.apply_style()

    def apply_style(self):
        ov = self.controller.cfg["overlay"]
        self.setWindowOpacity(ov.get("opacity", 0.92))
        locked = ov.get("locked", False)
        if bool(self.windowFlags() & Qt.WindowTransparentForInput) != locked:
            visible = self.isVisible()
            self.setWindowFlag(Qt.WindowTransparentForInput, locked)
            if visible:
                self.show()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.windowHandle().startSystemMove()
        elif e.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction("Hide", lambda: self.controller.hide_overlay(self.wid))
            menu.addAction("Open control panel", self.controller.show_main)
            menu.exec(e.globalPosition().toPoint())

    def moveEvent(self, e):
        self.controller.overlay_moved(self.wid, self.x(), self.y())

    def background(self, p):
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)
        p.fillPath(path, QColor(12, 14, 19, 220))
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.drawPath(path)


class CooldownOverlay(Overlay):
    def __init__(self, controller, wid):
        super().__init__(controller, wid, 250, 50)
        self.name = wid.split(":", 1)[1]

    def paintEvent(self, e):
        ov = self.controller.cfg["overlay"]
        flat = ov.get("bar_style", "card") == "flat"
        size = (ov.get("flat_width", 200), ov.get("flat_height", 12)) if flat else (250, 50)
        if (self.width(), self.height()) != size:
            self.resize(*size)
            return
        p = QPainter(self)
        cd = self.controller.engine.cooldown(self.name)
        if flat:
            self.paint_flat(p, cd)
            return
        self.background(p)
        p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        p.setPen(TEXT)
        name_w = p.fontMetrics().horizontalAdvance(self.name)
        p.drawText(QRectF(14, 6, 150, 20), Qt.AlignVCenter | Qt.AlignLeft, self.name)
        if cd is None:
            return
        # Little on/off tags for resets triggered by another key, e.g. "BD" for Blade Dancer.
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        x = 14 + name_w + 8
        for r in cd.resets:
            if r.key == cd.key:
                continue
            tag = "".join(w[0] for w in r.name.split("(")[0].split() if w[0].isalpha()).upper()[:3] or "R"
            w = p.fontMetrics().horizontalAdvance(tag) + 10
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(READY if r.armed else QColor(60, 66, 80)))
            p.drawRoundedRect(QRectF(x, 10, w, 13), 4, 4)
            p.setPen(QColor(12, 14, 19) if r.armed else MUTED)
            p.drawText(QRectF(x, 10, w, 13), Qt.AlignCenter, tag)
            x += w + 4
        p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        t = combat.now()
        left = cd.remaining(t)
        since_land = t - cd.landed_at
        flash = max(0.0, 1 - since_land / 0.6)
        if flash > 0:
            status, colour = "LANDED", LANDED
        elif left == 0:
            status, colour = "READY", READY
        else:
            status, colour = f"{left:.1f}s", TEXT
        p.setPen(colour)
        p.drawText(QRectF(self.width() - 100, 6, 86, 20), Qt.AlignVCenter | Qt.AlignRight, status)

        bar = QRectF(14, 31, self.width() - 28, 8)
        track = QPainterPath()
        track.addRoundedRect(bar, 4, 4)
        p.fillPath(track, QColor(38, 43, 54))
        frac = 1 - left / cd.span()
        if frac > 0:
            fill = QPainterPath()
            fill.addRoundedRect(QRectF(bar.x(), bar.y(), bar.width() * frac, bar.height()), 4, 4)
            p.fillPath(fill, READY if left == 0 else QColor(cd.color))
        if flash > 0:
            glow = QColor(LANDED)
            glow.setAlphaF(0.7 * flash)
            p.fillPath(track, glow)
        if cd.cancel_cooldown:
            cleft = cd.cancel_remaining(t)
            if cleft:
                w = bar.width() * cleft / cd.cancel_cooldown
                p.fillRect(QRectF(bar.x(), bar.bottom() + 3, w, 2), QColor("#c084fc"))


    def paint_flat(self, p, cd):
        """A plain thick bar in the cooldown's own colour, filling up as it recharges."""
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.fillRect(rect, QColor(30, 34, 42, 235))
        if cd is not None:
            t = combat.now()
            frac = min(1 - cd.remaining(t) / cd.span(), 1)
            if frac > 0:
                p.fillRect(QRectF(rect.x(), rect.y(), rect.width() * frac, rect.height()), QColor(cd.color))
            flash = max(0.0, 1 - (t - cd.landed_at) / 0.6)
            if flash > 0:
                glow = QColor(255, 255, 255)
                glow.setAlphaF(0.75 * flash)
                p.fillRect(rect, glow)
        outline = self.controller.cfg["overlay"].get("flat_outline", 1)
        if outline:
            p.setPen(QPen(QColor(8, 10, 14), outline, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect.adjusted(outline / 2 - 0.5, outline / 2 - 0.5, 0.5 - outline / 2, 0.5 - outline / 2))


class StatusOverlay(Overlay):
    def __init__(self, controller, wid):
        super().__init__(controller, wid, 190, 32)

    def paintEvent(self, e):
        p = QPainter(self)
        self.background(p)
        eng = self.controller.engine
        if not eng.active:
            dot, text = MUTED, "Macros OFF"
        elif eng.game_focused():
            dot, text = READY, "Macros ON"
        else:
            dot, text = QColor("#f59e0b"), "ON - game not focused"
        p.setBrush(dot)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(12, 11, 10, 10))
        p.setPen(TEXT)
        p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        p.drawText(QRectF(30, 0, self.width() - 36, self.height()), Qt.AlignVCenter, text)


class MacrosOverlay(Overlay):
    ROW = 22

    def __init__(self, controller, wid):
        super().__init__(controller, wid, 230, 40)

    def paintEvent(self, e):
        macros = self.controller.engine.macros
        want_h = 34 + self.ROW * max(len(macros), 1)
        if self.height() != want_h:
            self.resize(self.width(), want_h)
            return
        p = QPainter(self)
        self.background(p)
        on = self.controller.engine.active
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.setPen(READY if on else MUTED)
        p.drawText(QRectF(14, 6, 200, 20), Qt.AlignVCenter, "MACROS ON" if on else "MACROS OFF")
        p.setFont(QFont("Segoe UI", 9))
        if not macros:
            p.setPen(MUTED)
            p.drawText(QRectF(14, 30, 200, 20), Qt.AlignVCenter, "no macros")
        for i, m in enumerate(macros):
            y = 30 + i * self.ROW
            key = QRectF(14, y + 2, 46, 17)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(38, 43, 54))
            p.drawRoundedRect(key, 4, 4)
            p.setPen(TEXT)
            p.drawText(key, Qt.AlignCenter, m.hotkey.replace("mouse_", "M-").upper())
            p.setPen(LANDED if m.running else (TEXT if on else MUTED))
            p.drawText(QRectF(68, y, self.width() - 80, self.ROW), Qt.AlignVCenter, m.name)


class PartyOverlay(Overlay):
    """You and each friend as a bar card in the same style as the Parry / Dodge bars."""
    HEADER = 26
    ROW = 54

    def __init__(self, controller, wid):
        super().__init__(controller, wid, 330, 70)

    def paintEvent(self, e):
        rows = list(self.controller.engine.party)
        want_h = self.HEADER + 8 + self.ROW * max(len(rows), 1)
        if self.height() != want_h:
            self.resize(self.width(), want_h)
            return
        p = QPainter(self)
        self.background(p)
        pcfg = self.controller.cfg.get("party", {})
        link = self.controller.engine.party_link
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        p.setPen(READY if link.status == "connected" else MUTED)
        p.drawText(QRectF(14, 6, 120, 16), Qt.AlignVCenter, "PARTY HP")
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(MUTED)
        p.drawText(QRectF(110, 6, self.width() - 124, 16), Qt.AlignVCenter | Qt.AlignRight,
                   link.status if pcfg.get("enabled") else "off")
        if not rows:
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRectF(14, self.HEADER + 8, self.width() - 28, 20), Qt.AlignVCenter,
                       "turn on in the Party HP page")
            return
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
        for i, row in enumerate(rows):
            name, frac, online, is_you = row["name"], row["hp"], row["online"], row["you"]
            y = self.HEADER + 4 + i * self.ROW
            low = online and frac is not None and frac < 0.5
            if low:
                # Under 50%: the whole row pulses red so it catches your eye.
                glow = QColor(239, 68, 68)
                glow.setAlphaF(0.12 + 0.22 * pulse)
                path = QPainterPath()
                path.addRoundedRect(QRectF(6, y - 2, self.width() - 12, self.ROW - 4), 6, 6)
                p.fillPath(path, glow)
            p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
            p.setPen(TEXT if online else MUTED)
            label = name + ("  (you)" if is_you else "")
            p.drawText(QRectF(14, y, self.width() - 100, 18), Qt.AlignVCenter, label)
            if online and row.get("combat"):
                # In PvP combat: a red tag with how many players are on them.
                x = 14 + p.fontMetrics().horizontalAdvance(label) + 8
                tag = "PVP" + (f" x{row['count']}" if row.get("count") else "")
                p.setFont(QFont("Segoe UI", 7, QFont.Bold))
                tw = p.fontMetrics().horizontalAdvance(tag) + 10
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(220, 38, 38))
                p.drawRoundedRect(QRectF(x, y + 3, tw, 13), 4, 4)
                p.setPen(QColor(255, 255, 255))
                p.drawText(QRectF(x, y + 3, tw, 13), Qt.AlignCenter, tag)
            if not online:
                status, colour = "offline", MUTED
            elif frac is None:
                status, colour = "?", MUTED
            else:
                status, colour = f"{frac:.0%}", hp_color(frac)
            p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
            p.setPen(colour)
            p.drawText(QRectF(self.width() - 86, y, 72, 18), Qt.AlignVCenter | Qt.AlignRight, status)
            # Second line: server and region, green when they're in your server.
            p.setFont(QFont("Segoe UI", 8))
            if online:
                parts = [row.get("server") or "server unknown"]
                if row.get("region"):
                    parts.append(row["region"])
                text = "  ·  ".join(parts)
                if row.get("same") and not is_you:
                    text += "  ·  same server"
                p.setPen(READY if row.get("same") else MUTED)
                p.drawText(QRectF(14, y + 17, self.width() - 28, 14), Qt.AlignVCenter, text)
            bar = QRectF(14, y + 34, self.width() - 28, 8)
            track = QPainterPath()
            track.addRoundedRect(bar, 4, 4)
            p.fillPath(track, QColor(38, 43, 54))
            if online and frac:
                fill = QPainterPath()
                fill.addRoundedRect(QRectF(bar.x(), bar.y(), bar.width() * frac, bar.height()), 4, 4)
                p.fillPath(fill, colour)


def make_overlay(controller, wid):
    if wid.startswith("cooldown:"):
        return CooldownOverlay(controller, wid)
    if wid == "status":
        return StatusOverlay(controller, wid)
    if wid == "macros":
        return MacrosOverlay(controller, wid)
    if wid == "party":
        return PartyOverlay(controller, wid)
    return None

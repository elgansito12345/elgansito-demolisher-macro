"""Elgansito Demolisher Macro control panel.

Run this file (or run.bat). Everything you change here saves to config.json
straight away and takes effect immediately.
"""
import copy
import ctypes
import os
import re
import sys
import time

# Work in real screen pixels so Qt, screen capture and clicks all agree.
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import cv2
from PySide6.QtCore import QMimeData, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QDrag, QFont, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow,
    QPlainTextEdit, QPushButton, QScrollArea, QSizeGrip, QSlider, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

import combat
import config
import detect
import engine as engine_mod
import fastflags
import overlays
import party
import sendinput

STYLE = """
* { font-family: "Segoe UI"; font-size: 10pt; color: #e6e8ee; }
QMainWindow, #Body { background: #14161b; }
#TitleBar { background: #0f1115; }
#Sidebar { background: #0f1115; }
#AppTitle { font-size: 11pt; font-weight: 600; }
#PageTitle { font-size: 16pt; font-weight: 600; }
#Hint, .hint { color: #8b93a5; }
QLabel { background: transparent; }
QPushButton { background: #232836; border: 1px solid #2e3445; border-radius: 7px; padding: 6px 12px; }
QPushButton:hover { background: #2b3142; }
QPushButton:pressed { background: #1d2230; }
QPushButton:disabled { color: #5c6375; }
QPushButton#Primary { background: #3b82f6; border: none; color: white; font-weight: 600; }
QPushButton#Primary:hover { background: #4b8ff8; }
QPushButton#Danger { background: transparent; border: 1px solid #5b2730; color: #f87171; }
QPushButton#Nav { text-align: left; padding: 9px 14px; border: none; border-radius: 8px;
                  background: transparent; color: #8b93a5; font-weight: 600; }
QPushButton#Nav:hover { color: #e6e8ee; background: #191c24; }
QPushButton#Nav:checked { color: #ffffff; background: #222838; }
QPushButton#TitleBtn { background: transparent; border: none; border-radius: 0; padding: 4px 14px; font-size: 11pt; }
QPushButton#TitleBtn:hover { background: #222838; }
QPushButton#CloseBtn { background: transparent; border: none; border-radius: 0; padding: 4px 14px; font-size: 11pt; }
QPushButton#CloseBtn:hover { background: #c42b1c; }
QPushButton#Toggle { font-size: 13pt; font-weight: 700; padding: 14px; border-radius: 12px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QListWidget {
    background: #1b1f29; border: 1px solid #2e3445; border-radius: 7px; padding: 5px 7px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #3b82f6; }
QComboBox QAbstractItemView { background: #1b1f29; selection-background-color: #2b3550; border: 1px solid #2e3445; }
QListWidget { padding: 4px; }
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #2b3550; color: white; }
QGroupBox { border: 1px solid #262b38; border-radius: 10px; margin-top: 16px; padding: 12px 10px 10px 10px;
            background: #171a21; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #aab2c3; }
QGroupBox::indicator, QCheckBox::indicator { width: 16px; height: 16px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #2e3445; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QSlider::groove:horizontal { height: 4px; background: #2e3445; border-radius: 2px; }
QSlider::handle:horizontal { background: #3b82f6; width: 14px; margin: -6px 0; border-radius: 7px; }
#Card { background: #1b1f29; border: 1px solid #2e3445; border-radius: 12px; }
#Card:hover { border-color: #3b82f6; }
#StepRow { background: #1b1f29; border: 1px solid #262b38; border-radius: 8px; }
"""


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "item"


def nice_key(name):
    if not name:
        return "not set"
    names = {"mouse_left": "Left mouse", "mouse_right": "Right mouse", "mouse_middle": "Middle mouse",
             "mouse_x1": "Mouse side 1", "mouse_x2": "Mouse side 2"}
    return names.get(name, name.upper() if len(name) == 1 else name.replace("_", " ").title())


def to_pixmap(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    return QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())


def hint(text):
    label = QLabel(text)
    label.setObjectName("Hint")
    label.setWordWrap(True)
    return label


def spin(value, lo, hi, on_change, suffix="", step=1):
    box = QSpinBox()
    box.setRange(lo, hi)
    box.setSingleStep(step)
    box.setValue(int(value))
    box.setSuffix(suffix)
    box.valueChanged.connect(on_change)
    return box


def combo(options, current, on_change, editable=False):
    """options: list of values, or dict value -> label."""
    box = QComboBox()
    box.setEditable(editable)
    items = options.items() if isinstance(options, dict) else [(o, o) for o in options]
    for value, label in items:
        box.addItem(label, value)
    idx = box.findData(current)
    if idx >= 0:
        box.setCurrentIndex(idx)
    elif editable:
        box.setEditText(str(current))
    if editable:
        box.currentTextChanged.connect(lambda text: on_change(text.strip().lower()))
    else:
        box.currentIndexChanged.connect(lambda _: on_change(box.currentData()))
    return box


def row(*widgets, stretch=True):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    for item in widgets:
        if isinstance(item, QLabel):
            item.setWordWrap(False)
        lay.addWidget(item)
    if stretch:
        lay.addStretch(1)
    return w


# ---- small reusable controls -----------------------------------------------

class KeyButton(QPushButton):
    """Click, then press any key or mouse button to set it."""

    def __init__(self, controller, value, on_change):
        super().__init__(nice_key(value))
        self.controller = controller
        self.value = value
        self.on_change = on_change
        self.setMinimumWidth(130)
        self.setToolTip("Click, then press a key or mouse button. Esc cancels.")
        self.clicked.connect(self.start)
        self.timer = QTimer(self, interval=30, timeout=self.poll)

    def start(self):
        eng = self.controller.engine
        eng.captured_key = None
        eng.capturing = True
        self.setText("press a key...")
        self.timer.start()

    def poll(self):
        eng = self.controller.engine
        if eng.captured_key is None:
            return
        self.timer.stop()
        key, eng.captured_key = eng.captured_key, None
        if key != "esc":
            self.value = key
            self.on_change(key)
        self.setText(nice_key(self.value))


class ColorButton(QPushButton):
    def __init__(self, rgb, on_change):
        super().__init__()
        self.on_change = on_change
        self.setFixedWidth(90)
        self.clicked.connect(self.choose)
        self.set_rgb(rgb, notify=False)

    def set_rgb(self, rgb, notify=True):
        self.rgb = list(rgb)
        r, g, b = self.rgb
        text = "#000" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "#fff"
        self.setText(f"{r},{g},{b}")
        self.setStyleSheet(f"background: rgb({r},{g},{b}); color: {text}; border: 1px solid #2e3445;")
        if notify:
            self.on_change(self.rgb)

    def choose(self):
        c = QColorDialog.getColor(QColor(*self.rgb), self, "Pick colour")
        if c.isValid():
            self.set_rgb([c.red(), c.green(), c.blue()])


class HexColorButton(ColorButton):
    """Same as ColorButton but stores '#rrggbb'."""

    def __init__(self, hex_colour, on_change):
        c = QColor(hex_colour)
        super().__init__([c.red(), c.green(), c.blue()], lambda rgb: on_change(QColor(*rgb).name()))


# ---- screen picker -----------------------------------------------------------

class ScreenPicker(QWidget):
    """Full-screen frozen screenshot: drag a box to pick an area, or click to pick a colour."""

    def __init__(self, image, origin, mode, callback):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.image = image
        self.pixmap = to_pixmap(image)
        self.origin = origin
        self.mode = mode
        self.callback = callback
        self.start = self.end = None
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setGeometry(origin[0], origin[1], self.pixmap.width(), self.pixmap.height())
        self.mouse = QPoint(0, 0)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.finish(None)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.finish(None)
            return
        self.start = self.end = e.position().toPoint()

    def mouseMoveEvent(self, e):
        self.mouse = e.position().toPoint()
        if self.start is not None:
            self.end = self.mouse
        self.update()

    def mouseReleaseEvent(self, e):
        if self.start is None:
            return
        p = e.position().toPoint()
        ox, oy = self.origin
        if self.mode == "area":
            rect = QRect(self.start, p).normalized()
            if rect.width() >= 4 and rect.height() >= 4:
                self.finish({"region": [rect.x() + ox, rect.y() + oy, rect.width(), rect.height()]})
            else:
                self.start = None
        else:
            x = min(max(p.x(), 0), self.image.shape[1] - 1)
            y = min(max(p.y(), 0), self.image.shape[0] - 1)
            b, g, r = (int(v) for v in self.image[y, x])
            self.finish({"point": [x + ox, y + oy], "color": [r, g, b]})

    def finish(self, result):
        self.close()
        self.callback(result, self.image, self.origin)

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(0, 0, self.pixmap)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        if self.mode == "area" and self.start is not None:
            rect = QRect(self.start, self.end).normalized()
            p.drawPixmap(rect, self.pixmap, rect)
            p.setPen(QPen(QColor("#3b82f6"), 2))
            p.drawRect(rect)
            p.setPen(Qt.white)
            p.drawText(rect.bottomLeft() + QPoint(0, 16), f"{rect.width()} x {rect.height()}")
        if self.mode == "point":
            self.draw_magnifier(p)
        text = ("Drag a box around the area.  Esc / right-click to cancel." if self.mode == "area"
                else "Click the colour you want.  Esc / right-click to cancel.")
        p.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        box = QRectF(self.width() / 2 - 300, 24, 600, 40)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 17, 21, 230))
        p.drawRoundedRect(box, 10, 10)
        p.setPen(Qt.white)
        p.drawText(box, Qt.AlignCenter, text)

    def draw_magnifier(self, p):
        m = self.mouse
        src = QRect(m.x() - 7, m.y() - 7, 15, 15)
        dest = QRect(m.x() + 20, m.y() + 20, 150, 150)
        if dest.right() > self.width():
            dest.moveRight(m.x() - 20)
        if dest.bottom() > self.height():
            dest.moveBottom(m.y() - 20)
        p.drawPixmap(dest, self.pixmap, src)
        p.setPen(QPen(QColor("#3b82f6"), 2))
        p.drawRect(dest)
        cell = dest.width() / 15
        p.setPen(QPen(Qt.white, 1))
        p.drawRect(QRectF(dest.x() + 7 * cell, dest.y() + 7 * cell, cell, cell))
        x = min(max(m.x(), 0), self.image.shape[1] - 1)
        y = min(max(m.y(), 0), self.image.shape[0] - 1)
        b, g, r = (int(v) for v in self.image[y, x])
        p.fillRect(QRect(dest.x(), dest.bottom() + 4, dest.width(), 22), QColor(15, 17, 21, 230))
        p.drawText(QRect(dest.x(), dest.bottom() + 4, dest.width(), 22), Qt.AlignCenter, f"rgb {r}, {g}, {b}")


# ---- detector editor (shared by cooldown landing + screen rules) -----------

class DetectorEditor(QWidget):
    def __init__(self, controller, spec, types, on_change, snapshot_name=None):
        super().__init__()
        self.c = controller
        self.spec = spec
        self.on_change = on_change
        self.snapshot_name = snapshot_name
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignRight)

        self.type_box = combo({t: detect.TYPES[t] for t in types}, spec["type"], self.set_type)
        form.addRow("Look for", self.type_box)

        self.region_spins = []
        region = spec.get("region") or [0, 0, 100, 100]
        for i in range(4):
            self.region_spins.append(spin(region[i], 0 if i < 2 else 1, 20000, lambda v, i=i: self.set_region(i, v)))
            self.region_spins[i].setFixedWidth(84)
        self.pick_area_btn = QPushButton("Pick area")
        self.pick_area_btn.clicked.connect(lambda: self.pick("area"))
        self.region_row = row(*self.region_spins, self.pick_area_btn)
        form.addRow("Area (x, y, w, h)", self.region_row)

        self.color_btn = ColorButton(spec.get("color", [255, 255, 255]), lambda rgb: self.set("color", rgb))
        self.pick_color_btn = QPushButton("Pick colour")
        self.pick_color_btn.clicked.connect(lambda: self.pick("point"))
        self.tol = spin(spec.get("tolerance", 30), 0, 255, lambda v: self.set("tolerance", v))
        self.color_row = row(self.color_btn, self.pick_color_btn, QLabel("tolerance"), self.tol)
        form.addRow("Colour", self.color_row)

        self.frac = QDoubleSpinBox()
        self.frac.setRange(0.1, 100)
        self.frac.setDecimals(1)
        self.frac.setSingleStep(0.5)
        self.frac.setSuffix(" %")
        self.frac.setValue(spec.get("min_fraction", 0.04) * 100)
        self.frac.valueChanged.connect(lambda v: self.set("min_fraction", round(v / 100, 4)))
        self.frac_row = row(self.frac, hint("of the area must be that colour"))
        form.addRow("Needs", self.frac_row)

        self.point_lbl = QLabel()
        self.point_row = row(self.point_lbl, hint("set by Pick colour"))
        form.addRow("Pixel", self.point_row)

        self.tpl_lbl = QLabel()
        self.capture_btn = QPushButton("Capture picture")
        self.capture_btn.setToolTip("Drag a box around the thing to find. The search area is set a bit bigger.")
        self.capture_btn.clicked.connect(lambda: self.pick("area", capture=True))
        self.tpl_row = row(self.tpl_lbl, self.capture_btn)
        form.addRow("Picture", self.tpl_row)
        self.thr = QDoubleSpinBox()
        self.thr.setRange(0.3, 1.0)
        self.thr.setSingleStep(0.02)
        self.thr.setValue(spec.get("threshold", 0.8))
        self.thr.valueChanged.connect(lambda v: self.set("threshold", round(v, 3)))
        self.thr_row = row(self.thr, hint("match needed (0.8 is a good start)"))
        form.addRow("Match", self.thr_row)

        self.use_snapshot = QCheckBox("Pick from the recorded landing instead of the live screen")
        form.addRow("", self.use_snapshot)

        self.test_btn = QPushButton("Test on screen now")
        self.test_btn.clicked.connect(self.test)
        self.test_lbl = hint("")
        form.addRow("", row(self.test_btn, self.test_lbl))
        self.refresh()

    def set(self, key, value):
        self.spec[key] = value
        self.on_change()
        self.refresh()

    def set_type(self, t):
        self.set("type", t)

    def set_region(self, i, v):
        region = list(self.spec.get("region") or [0, 0, 100, 100])
        region[i] = v
        self.spec["region"] = region
        self.on_change()

    def refresh(self):
        t = self.spec["type"]
        self.region_row.setVisible(t != "pixel")
        self.color_row.setVisible(t != "image")
        self.frac_row.setVisible(t == "color_area")
        self.point_row.setVisible(t == "pixel")
        self.tpl_row.setVisible(t == "image")
        self.thr_row.setVisible(t == "image")
        self.form().labelForField(self.region_row).setVisible(t != "pixel")
        self.form().labelForField(self.color_row).setVisible(t != "image")
        self.form().labelForField(self.frac_row).setVisible(t == "color_area")
        self.form().labelForField(self.point_row).setVisible(t == "pixel")
        self.form().labelForField(self.tpl_row).setVisible(t == "image")
        self.form().labelForField(self.thr_row).setVisible(t == "image")
        self.point_lbl.setText("({}, {})".format(*self.spec.get("point", [0, 0])))
        self.tpl_lbl.setText(os.path.basename(self.spec.get("template") or "") or "none yet")
        region = self.spec.get("region") or [0, 0, 100, 100]
        for s, v in zip(self.region_spins, region):
            s.blockSignals(True)
            s.setValue(int(v))
            s.blockSignals(False)
        has_snap = bool(self.snapshot_name and self.snapshot_name in self.c.snapshots)
        self.use_snapshot.setVisible(has_snap)

    def form(self):
        return self.layout()

    def pick(self, mode, capture=False):
        source = None
        if self.use_snapshot.isVisible() and self.use_snapshot.isChecked():
            source = self.c.snapshots[self.snapshot_name]
        self.c.pick(mode, lambda res, img, origin: self.picked(res, img, origin, capture), source)

    def picked(self, result, image, origin, capture):
        if not result:
            return
        if "region" in result:
            x, y, w, h = result["region"]
            if capture or self.spec["type"] == "image":
                ox, oy = origin
                crop = image[y - oy:y - oy + h, x - ox:x - ox + w]
                os.makedirs(config.TEMPLATE_DIR, exist_ok=True)
                name = f"{slug(self.c.current_name())}_{int(time.time())}.png"
                detect.write_image(os.path.join(config.TEMPLATE_DIR, name), crop)
                self.spec["template"] = f"templates/{name}"
                m = 40
                self.spec["region"] = [max(x - m, 0), max(y - m, 0), w + 2 * m, h + 2 * m]
            else:
                self.spec["region"] = [x, y, w, h]
        else:
            self.spec["color"] = result["color"]
            self.color_btn.set_rgb(result["color"], notify=False)
            if self.spec["type"] == "pixel":
                self.spec["point"] = result["point"]
        self.on_change()
        self.refresh()

    def test(self):
        try:
            det = detect.Detector(self.spec)
            found, score, pos = det.check_now(self.c.cfg.get("monitor", 1))
            where = f" at {pos}" if pos else ""
            self.test_lbl.setText(("FOUND" if found else "not found") + f" - {detect.describe_score(det, score)}{where}")
        except Exception as e:
            self.test_lbl.setText(f"can't test: {e}")


# ---- pages ---------------------------------------------------------------------

class Page(QWidget):
    title = ""
    subtitle = ""

    def __init__(self, controller):
        super().__init__()
        self.c = controller
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 20, 26, 20)
        outer.setSpacing(4)
        t = QLabel(self.title)
        t.setObjectName("PageTitle")
        outer.addWidget(t)
        if self.subtitle:
            outer.addWidget(hint(self.subtitle))
        outer.addSpacing(10)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)

    def shown(self):
        pass

    def tick(self):
        pass


class HomePage(Page):
    title = "Home"
    subtitle = "Turn macros on, then switch to the game. Everything also works from the overlays."

    def __init__(self, controller):
        super().__init__(controller)
        self.toggle = QPushButton()
        self.toggle.setObjectName("Toggle")
        self.toggle.clicked.connect(lambda: self.c.engine.set_active(not self.c.engine.active))
        self.body.addWidget(self.toggle)
        self.status = QLabel()
        self.body.addWidget(self.status)
        self.stats = QLabel()
        self.stats.setObjectName("Hint")
        self.body.addWidget(self.stats)
        self.body.addWidget(QLabel("Activity"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        self.body.addWidget(self.log, 1)
        self.seq = 0

    def tick(self):
        eng = self.c.engine
        on = eng.active
        key = nice_key(self.c.cfg.get("toggle_key"))
        self.toggle.setText(f"Macros {'ON' if on else 'OFF'}   ({key} to toggle)")
        self.toggle.setStyleSheet("background: #15803d; border: none;" if on else "")
        game = self.c.cfg.get("game_window") or "any window"
        focus = "focused" if eng.game_focused() else "not focused"
        playing = eng.current_game() or (f"place {eng.place_id}" if eng.universe_id else "not in a game")
        self.status.setText(f"Game window: <b>{game}</b> ({focus})     Roblox: <b>{playing}</b>")
        parts = []
        for cd in eng.cooldowns:
            bits = [f"used {cd.uses}"]
            if cd.cancel_key:
                bits.append(f"cancelled {cd.cancels}")
            for r in cd.resets:
                if r.armed or r.hits:
                    bits.append(f"{r.name.lower()} {r.hits}")
            parts.append(f"{cd.name}: " + ", ".join(bits))
        for m in eng.macros:
            parts.append(f"{m.name}: ran {m.runs}")
        self.stats.setText("     ".join(parts))
        for seq, line in eng.log.since(self.seq):
            self.seq = seq
            self.log.appendPlainText(line)


class WidgetCard(QFrame):
    def __init__(self, controller, wid, title, desc):
        super().__init__()
        self.c = controller
        self.wid = wid
        self.setObjectName("Card")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(110)
        lay = QVBoxLayout(self)
        t = QLabel(title)
        t.setStyleSheet("font-weight: 600; font-size: 11pt;")
        lay.addWidget(t)
        lay.addWidget(hint(desc))
        lay.addStretch(1)
        self.btn = QPushButton()
        self.btn.clicked.connect(self.toggle)
        lay.addWidget(row(self.btn, hint("or drag this card out")))
        self.refresh()
        self.press = None

    def refresh(self):
        self.btn.setText("Hide" if self.c.overlay_visible(self.wid) else "Show")

    def toggle(self):
        if self.c.overlay_visible(self.wid):
            self.c.hide_overlay(self.wid)
        else:
            self.c.show_overlay(self.wid)
        self.refresh()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self.press is None or (e.position().toPoint() - self.press).manhattanLength() < 12:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.wid)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab().scaledToWidth(220, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(20, 20))
        drag.exec(Qt.MoveAction)
        self.press = None
        self.c.show_overlay(self.wid, QCursor.pos() - QPoint(20, 20))
        self.refresh()


class WidgetsPage(Page):
    title = "Overlays"
    subtitle = ("Drag a card out of this window and drop it anywhere on your screen. Drag an overlay to move it, "
                "right-click it to hide it.")

    def __init__(self, controller):
        super().__init__(controller)
        ov = self.c.cfg["overlay"]
        self.lock = QCheckBox("Lock overlays (clicks go straight through to the game)")
        self.lock.setChecked(ov.get("locked", False))
        self.lock.toggled.connect(self.set_lock)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(30, 100)
        self.opacity.setValue(int(ov.get("opacity", 0.92) * 100))
        self.opacity.setFixedWidth(200)
        self.opacity.valueChanged.connect(self.set_opacity)
        self.body.addWidget(self.lock)
        self.body.addWidget(row(QLabel("Opacity"), self.opacity))

        def set_ov(key, value):
            self.c.cfg["overlay"][key] = value
            self.c.changed(apply=False)
        style = combo({"flat": "Flat bars (no text)", "card": "Cards (name + time)"}, ov.get("bar_style", "flat"),
                      lambda v: set_ov("bar_style", v))
        width = spin(ov.get("flat_width", 178), 40, 1200, lambda v: set_ov("flat_width", v), " px", 10)
        height = spin(ov.get("flat_height", 12), 2, 80, lambda v: set_ov("flat_height", v), " px")
        outline = spin(ov.get("flat_outline", 1), 0, 10, lambda v: set_ov("flat_outline", v), " px")
        self.body.addWidget(row(QLabel("Parry / Dodge bars"), style))
        self.body.addWidget(row(QLabel("Length"), width, QLabel("Thickness"), height, QLabel("Outline"), outline))
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 8, 0, 0)
        self.grid.setSpacing(12)
        self.body.addWidget(self.grid_host)
        self.body.addStretch(1)
        self.cards = []

    def set_lock(self, on):
        self.c.cfg["overlay"]["locked"] = on
        self.c.restyle_overlays()
        self.c.changed(apply=False)

    def set_opacity(self, v):
        self.c.cfg["overlay"]["opacity"] = v / 100
        self.c.restyle_overlays()
        self.c.changed(apply=False)

    def shown(self):
        for card in self.cards:
            card.setParent(None)
        self.cards = []
        for i, (wid, title, desc) in enumerate(overlays.widget_catalog(self.c.cfg)):
            card = WidgetCard(self.c, wid, title, desc)
            self.grid.addWidget(card, i // 3, i % 3)
            self.cards.append(card)

    def tick(self):
        for card in self.cards:
            card.refresh()


class ListPage(Page):
    """A list of items on the left and an editor for the selected one on the right."""
    list_key = ""
    add_label = "Add"

    def __init__(self, controller):
        super().__init__(controller)
        split = QHBoxLayout()
        split.setSpacing(16)
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(200)
        self.list.currentRowChanged.connect(self.select)
        left.addWidget(self.list, 1)
        add = QPushButton(self.add_label)
        add.setObjectName("Primary")
        add.clicked.connect(self.add)
        dup = QPushButton("Duplicate")
        dup.clicked.connect(self.duplicate)
        delete = QPushButton("Delete")
        delete.setObjectName("Danger")
        delete.clicked.connect(self.delete)
        left.addWidget(add)
        left.addWidget(row(dup, delete, stretch=False))
        split.addLayout(left)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        split.addWidget(self.scroll, 1)
        self.body.addLayout(split, 1)
        self.editor = None

    @property
    def items(self):
        return self.c.cfg[self.list_key]

    def shown(self):
        current = max(self.list.currentRow(), 0)
        self.list.blockSignals(True)
        self.list.clear()
        for item in self.items:
            self.list.addItem(self.label_for(item))
        self.list.blockSignals(False)
        if self.items:
            self.list.setCurrentRow(min(current, len(self.items) - 1))
            self.select(self.list.currentRow())
        else:
            self.select(-1)

    def label_for(self, item):
        return item["name"]

    def update_label(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.items):
            self.list.item(i).setText(self.label_for(self.items[i]))

    def unique(self, name):
        names = {i["name"] for i in self.items}
        base, n = name, 2
        while name in names:
            name = f"{base} {n}"
            n += 1
        return name

    def select(self, i):
        self.c.selected_name = self.items[i]["name"] if 0 <= i < len(self.items) else ""
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 14, 0)
        if 0 <= i < len(self.items):
            self.build(lay, self.items[i])
        else:
            lay.addWidget(hint("Nothing here yet. Press the button on the left to add one."))
        lay.addStretch(1)
        self.scroll.setWidget(holder)

    def add(self):
        self.items.append(self.new_item(self.unique(self.new_name)))
        self.c.changed()
        self.shown()
        self.list.setCurrentRow(len(self.items) - 1)

    def duplicate(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.items):
            item = copy.deepcopy(self.items[i])
            item["name"] = self.unique(item["name"])
            self.items.insert(i + 1, item)
            self.c.changed()
            self.shown()
            self.list.setCurrentRow(i + 1)

    def delete(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.items):
            self.deleted(self.items.pop(i))
            self.c.changed()
            self.shown()

    def deleted(self, item):
        pass

    def name_field(self, item, form, on_rename=None):
        edit = QLineEdit(item["name"])

        def done():
            new = edit.text().strip() or item["name"]
            if new != item["name"]:
                others = {i["name"] for i in self.items if i is not item}
                if new in others:
                    edit.setText(item["name"])
                    return
                old, item["name"] = item["name"], new
                if on_rename:
                    on_rename(old, new)
                self.c.changed()
                self.update_label()
        edit.editingFinished.connect(done)
        form.addRow("Name", edit)


def form_group(title, checkable=False, checked=True, on_toggle=None):
    box = QGroupBox(title)
    if checkable:
        box.setCheckable(True)
        box.setChecked(checked)
        box.toggled.connect(on_toggle)
    form = QFormLayout(box)
    form.setLabelAlignment(Qt.AlignRight)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(8)
    return box, form


class CooldownsPage(ListPage):
    title = "Cooldowns"
    subtitle = "Bars that time your dodge, parry or any other key from the moment you press it."
    list_key = "cooldowns"
    add_label = "Add cooldown"
    new_name = "New cooldown"

    def new_item(self, name):
        return config.new_cooldown(name)

    def deleted(self, item):
        self.c.hide_overlay(f"cooldown:{item['name']}")

    def build(self, lay, cd):
        ch = self.c.changed
        box, form = form_group("General")
        self.name_field(cd, form, lambda old, new: self.c.rename_overlay(f"cooldown:{old}", f"cooldown:{new}"))
        form.addRow("Key", KeyButton(self.c, cd["key"], lambda k: (cd.__setitem__("key", k), ch())))
        form.addRow("Cooldown", spin(cd["cooldown_ms"], 50, 120000,
                                     lambda v: (cd.__setitem__("cooldown_ms", v), ch()), " ms", 50))
        form.addRow("Bar colour", HexColorButton(cd.get("color", "#4aa3ff"),
                                                 lambda h: (cd.__setitem__("color", h), ch())))
        form.addRow("Game bubble", row(combo({0: "none", 1: "1st (roll)", 2: "2nd (parry)", 3: "3rd", 4: "4th"},
                                             cd.get("icon_slot", 0),
                                             lambda v: (cd.__setitem__("icon_slot", v), ch())),
                                       hint("syncs this bar with the game's cooldown bubble under your health bar")))
        live = self.c.engine.cooldown(cd["name"])
        if live and live.natural:
            form.addRow("", hint(f"learned from the game: {live.span():.2f}s per use "
                                 f"(from {len(live.natural)} full cooldowns)"))
        show = QPushButton("Show bar on screen")
        show.clicked.connect(lambda: self.c.show_overlay(f"cooldown:{cd['name']}"))
        form.addRow("", show)
        lay.addWidget(box)

        cancel = cd["cancel"]
        box, form = form_group("Cancel gives it back (roll cancel)", True, cancel.get("enabled", False),
                               lambda on: (cancel.__setitem__("enabled", on), ch()))
        form.addRow(hint("If you press the cancel key soon enough after using this, the cooldown is refunded."))
        form.addRow("Cancel key", KeyButton(self.c, cancel.get("key", "mouse_right"),
                                            lambda k: (cancel.__setitem__("key", k), ch())))
        form.addRow("Within", spin(cancel.get("window_ms", 350), 10, 5000,
                                   lambda v: (cancel.__setitem__("window_ms", v), ch()), " ms", 10))
        form.addRow("Cancel cooldown", spin(cancel.get("cooldown_ms", 0), 0, 60000,
                                            lambda v: (cancel.__setitem__("cooldown_ms", v), ch()), " ms", 50))
        form.addRow("Free cancels", spin(cancel.get("max_refunds", 1), 0, 10,
                                         lambda v: (cancel.__setitem__("max_refunds", v), ch()), " in a row"))
        form.addRow(hint("Deepwoken: the first roll cancel gives the roll back, but cancelling that extra roll "
                         "too puts it on cooldown - so 1."))
        lay.addWidget(box)

        self.reset_widgets = {}
        for r in cd["resets"]:
            self.build_reset(lay, cd, r)
        add = QPushButton("+ Add reset trigger")
        add.setToolTip("Something seen on screen after a key press that makes this ready again")
        add.clicked.connect(lambda: self.add_reset(cd))
        lay.addWidget(row(add))

    def add_reset(self, cd):
        names = {r["name"] for r in cd["resets"]}
        name, n = "New reset", 2
        while name in names:
            name, n = f"New reset {n}", n + 1
        cd["resets"].append(config.new_reset(name, cd["key"]))
        self.c.changed()
        self.select(self.list.currentRow())

    def build_reset(self, lay, cd, r):
        ch = self.c.changed
        box, form = form_group(f"Reset: {r['name']}", True, r.get("enabled", False),
                               lambda on: (r.__setitem__("enabled", on), ch()))
        form.addRow(hint(f"Makes {cd['name']} ready again when the effect below shows up shortly after you press "
                         "the trigger key. Set it up: press Record, do it once in game, then come back and pick "
                         "the effect's area and colour from the recording."))
        name = QLineEdit(r["name"])

        def rename():
            new = name.text().strip()
            if new and new != r["name"] and new not in {x["name"] for x in cd["resets"]}:
                r["name"] = new
                box.setTitle(f"Reset: {new}")
                ch()
            else:
                name.setText(r["name"])
        name.editingFinished.connect(rename)
        form.addRow("Name", name)
        form.addRow("Trigger key", KeyButton(self.c, r.get("key", ""), lambda k: (r.__setitem__("key", k), ch())))
        toggle = KeyButton(self.c, r.get("toggle_key", ""), lambda k: (r.__setitem__("toggle_key", k), ch()))
        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: (r.__setitem__("toggle_key", ""), toggle.setText(nice_key("")), ch()))
        form.addRow("On/off hotkey", row(toggle, clear))
        form.addRow("Watch for", spin(r.get("window_ms", 450), 50, 3000,
                                      lambda v: (r.__setitem__("window_ms", v), ch()), " ms after the key", 25))
        record = QPushButton("Record next one")
        label = hint("")
        record.clicked.connect(lambda: self.record(cd, r, label))
        form.addRow("", row(record, label))
        det = DetectorEditor(self.c, r["detect"], ["color_area", "image"], ch,
                             snapshot_name=f"{cd['name']}/{r['name']}")
        form.addRow(det)
        delete = QPushButton("Delete this reset")
        delete.setObjectName("Danger")
        delete.clicked.connect(lambda: (cd["resets"].remove(r), ch(), self.select(self.list.currentRow())))
        form.addRow("", row(delete))
        self.reset_widgets[f"{cd['name']}/{r['name']}"] = (label, det)
        lay.addWidget(box)

    def record(self, cd, r, label):
        self.c.engine.snapshot_for = (cd["name"], r["name"])
        self.c.engine.snapshot_path = None
        label.setText(f"waiting - go in game and press {nice_key(r['key'])} so it lands")
        self.c.waiting_snapshot = self

    def snapshot_ready(self, name):
        widgets = getattr(self, "reset_widgets", {}).get(name)
        if not widgets:
            return
        label, det = widgets
        try:
            label.setText("recorded - now use Pick area / Pick colour below")
            det.refresh()
            det.use_snapshot.setChecked(True)
        except RuntimeError:
            pass  # editor was rebuilt


class StepRow(QFrame):
    def __init__(self, page, steps, index, on_change):
        super().__init__()
        self.setObjectName("StepRow")
        step = steps[index]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        num = QLabel(f"{index + 1}.")
        num.setFixedWidth(22)
        lay.addWidget(num)

        def set_action(a):
            step["action"] = a
            if a in combat.KEY_ACTIONS:
                step.setdefault("key", "e")
            elif a in combat.MOUSE_ACTIONS:
                step.setdefault("button", "left")
            step.setdefault("ms", 25 if a != "wait" else 50)
            on_change(rebuild=True)
        lay.addWidget(combo(combat.STEP_ACTIONS, step["action"], set_action))
        a = step["action"]
        if a in combat.KEY_ACTIONS:
            lay.addWidget(combo(sendinput.KEY_NAMES, step.get("key", "e"),
                                lambda k: (step.__setitem__("key", k), on_change()), editable=True))
        elif a in combat.MOUSE_ACTIONS:
            lay.addWidget(combo({b: nice_key(f"mouse_{b}") for b in sendinput.MOUSE_BUTTONS},
                                step.get("button", "left"), lambda b: (step.__setitem__("button", b), on_change())))
        if a in ("tap", "click", "wait"):
            label = "for" if a == "wait" else "hold"
            lay.addWidget(QLabel(label))
            lay.addWidget(spin(step.get("ms", 25), 0, 60000, lambda v: (step.__setitem__("ms", v), on_change()),
                               " ms", 5))
        lay.addStretch(1)
        for text, tip, fn in (("↑", "Move up", lambda: page.move_step(steps, index, -1)),
                              ("↓", "Move down", lambda: page.move_step(steps, index, 1)),
                              ("✕", "Delete step", lambda: page.delete_step(steps, index))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedWidth(34)
            b.clicked.connect(fn)
            lay.addWidget(b)


def describe_steps(steps):
    out = []
    for s in steps:
        a = s.get("action")
        if a == "tap":
            out.append(f"press {nice_key(s.get('key'))}")
        elif a == "down":
            out.append(f"hold {nice_key(s.get('key'))}")
        elif a == "up":
            out.append(f"release {nice_key(s.get('key'))}")
        elif a == "click":
            out.append(f"click {nice_key('mouse_' + s.get('button', 'left'))}")
        elif a == "mouse_down":
            out.append(f"hold {nice_key('mouse_' + s.get('button', 'left'))}")
        elif a == "mouse_up":
            out.append(f"release {nice_key('mouse_' + s.get('button', 'left'))}")
        elif a == "wait":
            out.append(f"wait {s.get('ms', 0)}ms")
        elif a == "wait_release":
            out.append("wait until you let go")
    return " → ".join(out) or "no steps"


class MacrosPage(ListPage):
    title = "Macros"
    subtitle = "Press a hotkey to run a list of steps: hold keys, press keys, click, wait."
    list_key = "macros"
    add_label = "Add macro"
    new_name = "New macro"

    def new_item(self, name):
        return config.new_macro(name)

    def label_for(self, m):
        state = "" if m.get("enabled", True) else "  (off)"
        return f"{m['name']}  [{nice_key(m.get('hotkey'))}]{state}"

    def build(self, lay, m):
        ch = self.c.changed

        def changed():
            ch()
            self.update_label()
            self.summary.setText(describe_steps(m["steps"]))

        box, form = form_group("Macro")
        self.name_field(m, form)
        enabled = QCheckBox("Enabled")
        enabled.setChecked(m.get("enabled", True))
        enabled.toggled.connect(lambda on: (m.__setitem__("enabled", on), changed()))
        form.addRow("", enabled)
        form.addRow("Hotkey", KeyButton(self.c, m.get("hotkey", ""), lambda k: (m.__setitem__("hotkey", k), changed())))
        block = QCheckBox("Replace the key: the game only gets what this macro sends (keyboard keys)")
        block.setToolTip("Needed when the macro re-sends its own hotkey, like F -> right click -> F.")
        block.setChecked(m.get("block_key", False))
        block.toggled.connect(lambda on: (m.__setitem__("block_key", on), ch()))
        form.addRow("", block)
        interval = spin(m.get("interval_ms", 100), 1, 60000, lambda v: (m.__setitem__("interval_ms", v), ch()),
                        " ms between repeats", 10)

        def set_mode(mode):
            m["mode"] = mode
            interval.setEnabled(mode != "once")
            ch()
        form.addRow("When pressed", combo(combat.MODES, m.get("mode", "once"), set_mode))
        interval.setEnabled(m.get("mode", "once") != "once")
        form.addRow("Repeat delay", interval)
        lay.addWidget(box)

        box = QGroupBox("Steps")
        steps_lay = QVBoxLayout(box)
        self.summary = hint(describe_steps(m["steps"]))
        steps_lay.addWidget(self.summary)
        self.steps_holder = QVBoxLayout()
        self.steps_holder.setSpacing(6)
        steps_lay.addLayout(self.steps_holder)
        add = QPushButton("+ Add step")
        add.clicked.connect(lambda: (m["steps"].append({"action": "tap", "key": "e", "ms": 25}),
                                     self.rebuild_steps(m, changed), changed()))
        steps_lay.addWidget(row(add))
        lay.addWidget(box)
        lay.addWidget(hint("Keys a macro sends still count towards your cooldown bars. Any held keys are released "
                           "when a macro ends or macros are turned off."))
        self.rebuild_steps(m, changed)

    def rebuild_steps(self, m, changed):
        while self.steps_holder.count():
            w = self.steps_holder.takeAt(0).widget()
            if w:
                w.setParent(None)

        def on_change(rebuild=False):
            changed()
            if rebuild:
                QTimer.singleShot(0, lambda: self.rebuild_steps(m, changed))
        self._step_change = on_change
        self._macro = m
        for i in range(len(m["steps"])):
            self.steps_holder.addWidget(StepRow(self, m["steps"], i, on_change))

    def move_step(self, steps, i, d):
        j = i + d
        if 0 <= j < len(steps):
            steps[i], steps[j] = steps[j], steps[i]
            self._step_change(rebuild=True)

    def delete_step(self, steps, i):
        steps.pop(i)
        self._step_change(rebuild=True)


class RulesPage(ListPage):
    title = "Screen rules"
    subtitle = "Watch the screen for a picture or colour, and react with a key press or click when it appears."
    list_key = "rules"
    add_label = "Add screen rule"
    new_name = "New screen rule"

    def new_item(self, name):
        return config.new_rule(name)

    def build(self, lay, r):
        ch = self.c.changed
        box, form = form_group("Rule")
        self.name_field(r, form)
        enabled = QCheckBox("Enabled")
        enabled.setChecked(r.get("enabled", True))
        enabled.toggled.connect(lambda on: (r.__setitem__("enabled", on), ch()))
        form.addRow("", enabled)
        self.live = hint("")
        form.addRow("Right now", self.live)
        lay.addWidget(box)

        box, form = form_group("What to look for")
        form.addRow(DetectorEditor(self.c, r["detect"], list(detect.TYPES), ch))
        lay.addWidget(box)

        a = r["action"]
        box, form = form_group("What to do")
        form.addRow("Fire", combo({"on_appear": "Once each time it appears",
                                   "while_visible": "Repeatedly while it's visible"},
                                  r.get("trigger", "on_appear"), lambda v: (r.__setitem__("trigger", v), ch())))
        form.addRow("At most every", spin(r.get("cooldown_ms", 500), 0, 600000,
                                          lambda v: (r.__setitem__("cooldown_ms", v), ch()), " ms", 50))
        key_box = combo(sendinput.KEY_NAMES, a.get("key", "space"),
                        lambda k: (a.__setitem__("key", k), ch()), editable=True)
        button_box = combo({b: nice_key(f"mouse_{b}") for b in sendinput.MOUSE_BUTTONS}, a.get("button", "left"),
                           lambda b: (a.__setitem__("button", b), ch()))
        at_box = combo({"match": "where it was found", "point": "a fixed spot"}, a.get("at", "match"),
                       lambda v: (a.__setitem__("at", v), ch(), sync()))
        point_lbl = QLabel("({}, {})".format(*a.get("point", [960, 540])))
        pick_point = QPushButton("Pick spot")

        def picked(res, img, origin):
            if res:
                a["point"] = res["point"]
                point_lbl.setText("({}, {})".format(*a["point"]))
                ch()
        pick_point.clicked.connect(lambda: self.c.pick("point", picked))
        ret = QCheckBox("Put the mouse back afterwards")
        ret.setChecked(a.get("return_mouse", True))
        ret.toggled.connect(lambda on: (a.__setitem__("return_mouse", on), ch()))
        rows = {"key": [("Key", key_box)],
                "click": [("Button", button_box), ("Click at", at_box), ("Spot", row(point_lbl, pick_point)),
                          ("", ret)]}

        def sync():
            kind = a.get("type", "none")
            for k, items in rows.items():
                for label, w in items:
                    visible = kind == k and not (label == "Spot" and a.get("at") != "point")
                    w.setVisible(visible)
                    lbl = form.labelForField(w)
                    if lbl:
                        lbl.setVisible(visible)
        form.addRow("Action", combo({"none": "Just show it", "key": "Press a key", "click": "Click"},
                                    a.get("type", "none"), lambda v: (a.__setitem__("type", v), ch(), sync())))
        for items in rows.values():
            for label, w in items:
                form.addRow(label, w)
        sync()
        lay.addWidget(box)

    def tick(self):
        if not hasattr(self, "live"):
            return
        try:
            rule = next((r for r in self.c.engine.rules if r.name == self.c.selected_name), None)
            if rule is None:
                self.live.setText("not running (disabled, or something needs fixing - see Home)")
            else:
                state = "FOUND" if rule.found else "not found"
                score = detect.describe_score(rule.detector, rule.score)
                where = f" at {rule.pos}" if rule.pos else ""
                self.live.setText(f"{state} - {score}{where} - fired {rule.fired}x")
        except RuntimeError:
            pass  # label was rebuilt


class PartyPage(Page):
    title = "Party HP"
    subtitle = ("Your HP is read off your own health bar. Friends who run Elgansito Demolisher Macro with the same party code "
                "share theirs, and everyone sees each other's HP as bars.")

    def __init__(self, controller):
        super().__init__(controller)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 14, 0)
        scroll.setWidget(holder)
        self.body.addWidget(scroll, 1)
        ch = self.c.changed

        # -- your HP
        my = self.c.cfg["my_hp"]
        box, form = form_group("Your HP")
        self.hp_now = QLabel()
        form.addRow("Right now", self.hp_now)
        self.region_spins = []
        for i in range(4):
            s = spin(my["region"][i], 0 if i < 2 else 10, 20000, lambda v, i=i: self.set_region(i, v))
            s.setFixedWidth(84)
            self.region_spins.append(s)
        pick = QPushButton("Pick area")
        pick.setToolTip("Drag a box around your health bar, a little taller than the bar.")
        pick.clicked.connect(self.pick_region)
        form.addRow("Health bar area", row(*self.region_spins, pick))
        self.cal_value = QSpinBox()
        self.cal_value.setRange(1, 100)
        self.cal_value.setSuffix(" %")
        self.cal_value.setValue(100)
        add_cal = QPushButton("Calibrate")
        add_cal.setToolTip("Type the % the game shows on your health bar right now, then press this.")
        add_cal.clicked.connect(self.add_calibration)
        reset_cal = QPushButton("Reset calibration")
        reset_cal.clicked.connect(self.reset_calibration)
        form.addRow("The game shows", row(self.cal_value, add_cal, reset_cal))
        self.cal_label = hint("")
        form.addRow("", self.cal_label)
        form.addRow(hint("The bar's fill isn't perfectly in step with the % the game prints. Every time you "
                         "calibrate at a different HP, readings get closer to exact."))
        lay.addWidget(box)

        # -- party
        pcfg = self.c.cfg["party"]
        box, form = form_group("Share with friends", True, pcfg.get("enabled", False),
                               lambda on: (pcfg.__setitem__("enabled", on), ch()))
        self.link_status = QLabel()
        form.addRow("Status", self.link_status)
        user = QLineEdit(pcfg.get("username", ""))
        user.setPlaceholderText("your Roblox username - this is the name friends see")
        user.editingFinished.connect(lambda: (pcfg.__setitem__("username", user.text().strip()), ch()))
        form.addRow("Your username", user)
        self.code = QLineEdit(pcfg.get("code", ""))
        self.code.setPlaceholderText("everyone in the party uses the same code")
        self.code.editingFinished.connect(lambda: (pcfg.__setitem__("code", self.code.text().strip()), ch()))
        new = QPushButton("New code")
        new.clicked.connect(self.new_code)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.code.text()))
        form.addRow("Party code", row(self.code, new, copy_btn, stretch=False))
        friends = QLineEdit(", ".join(pcfg.get("friends", [])))
        friends.setPlaceholderText("usernames to show, comma separated - empty shows everyone with the code")
        friends.editingFinished.connect(lambda: (pcfg.__setitem__(
            "friends", [f.strip() for f in friends.text().split(",") if f.strip()]), ch()))
        form.addRow("Friends", friends)
        show = QPushButton("Show Party HP on screen")
        show.setObjectName("Primary")
        show.clicked.connect(lambda: self.c.show_overlay("party"))
        form.addRow("", row(show))
        form.addRow(hint("Each friend needs Elgansito Demolisher Macro, their own username, and the same party code. Only your "
                         "username and HP % are sent, encrypted with the party code, through a free public relay "
                         f"({pcfg.get('broker', 'broker.emqx.io')})."))
        lay.addWidget(box)

        # -- key prompts
        pr = self.c.cfg["prompts"]
        box, form = form_group("Press Z / X / C / V prompts", True, pr.get("enabled", False),
                               lambda on: (pr.__setitem__("enabled", on), ch()))
        form.addRow(hint("When Deepwoken shows a Z, X, C or V prompt, it's pressed for you (while macros are ON "
                         "and the game is focused). Fake prompts on a teal box are never pressed."))
        self.prompt_now = QLabel()
        form.addRow("Right now", self.prompt_now)
        thr = QDoubleSpinBox()
        thr.setRange(0.5, 0.99)
        thr.setSingleStep(0.01)
        thr.setValue(pr.get("threshold", 0.82))
        thr.valueChanged.connect(lambda v: (pr.__setitem__("threshold", round(v, 2)), ch()))
        form.addRow("Match needed", row(thr, hint("raise it if it presses things that aren't prompts")))
        form.addRow("Delay before pressing", spin(pr.get("delay_ms", 0), 0, 2000,
                                                  lambda v: (pr.__setitem__("delay_ms", v), ch()), " ms", 10))
        self.prompt_spins = []
        for i in range(4):
            s = spin((pr.get("region") or [0, 0, 1920, 1080])[i], 0 if i < 2 else 10, 20000,
                     lambda v, i=i: self.set_prompt_region(i, v))
            s.setFixedWidth(84)
            self.prompt_spins.append(s)
        ppick = QPushButton("Pick area")
        ppick.setToolTip("Drag a box over where the prompts appear. Smaller is faster and avoids false matches.")
        ppick.clicked.connect(self.pick_prompt_region)
        form.addRow("Search area", row(*self.prompt_spins, ppick))
        lay.addWidget(box)
        lay.addStretch(1)
        self.refresh_calibration()

    # your HP
    def set_region(self, i, v):
        self.c.cfg["my_hp"]["region"][i] = v
        self.c.changed()

    def pick_region(self):
        def picked(res, img, origin):
            if res and "region" in res:
                self.c.cfg["my_hp"]["region"] = res["region"]
                for s, v in zip(self.region_spins, res["region"]):
                    s.blockSignals(True)
                    s.setValue(v)
                    s.blockSignals(False)
                self.c.changed()
        self.c.pick("area", picked)

    def add_calibration(self):
        raw = self.c.engine.my_hp_raw
        if raw is None:
            self.cal_label.setText("can't see your health bar right now - go in game first")
            return
        cal = self.c.cfg["my_hp"].setdefault("calibration", [])
        cal[:] = [pt for pt in cal if abs(pt[0] - raw) > 0.005]
        cal.append([round(raw, 4), self.cal_value.value() / 100])
        self.c.changed()
        self.refresh_calibration()

    def reset_calibration(self):
        self.c.cfg["my_hp"]["calibration"] = []
        self.c.changed()
        self.refresh_calibration()

    def refresh_calibration(self):
        pts = sorted(self.c.cfg["my_hp"].get("calibration", []))
        self.cal_label.setText("calibrated at: " + (", ".join(f"{b:.0%}" for _, b in pts) or "nothing yet (raw fill)"))

    # party
    def new_code(self):
        self.code.setText(party.new_code())
        self.c.cfg["party"]["code"] = self.code.text()
        self.c.changed()

    # prompts
    def set_prompt_region(self, i, v):
        region = self.c.cfg["prompts"].get("region") or [0, 0, 1920, 1080]
        region[i] = v
        self.c.cfg["prompts"]["region"] = region
        self.c.changed()

    def pick_prompt_region(self):
        def picked(res, img, origin):
            if res and "region" in res:
                self.c.cfg["prompts"]["region"] = res["region"]
                for s, v in zip(self.prompt_spins, res["region"]):
                    s.blockSignals(True)
                    s.setValue(v)
                    s.blockSignals(False)
                self.c.changed()
        self.c.pick("area", picked)

    def tick(self):
        eng = self.c.engine
        if eng.my_hp is None:
            self.hp_now.setText("can't see your health bar (go in game, or Pick area)")
        else:
            self.hp_now.setText(f"<b>{eng.my_hp}%</b>   (raw fill {eng.my_hp_raw:.3f})")
        self.link_status.setText(eng.party_link.status)
        seen = eng.prompt_seen
        if not self.c.cfg["prompts"].get("enabled"):
            self.prompt_now.setText("off")
        elif not (eng.active and eng.game_focused()):
            self.prompt_now.setText("waiting for macros ON + game focused")
        elif seen:
            self.prompt_now.setText(f"best match {seen[0]} {seen[1]:.2f}{' (fake)' if seen[2] else ''}"
                                    f"  -  pressed {eng.prompt_presses}")
        else:
            self.prompt_now.setText(f"watching  -  pressed {eng.prompt_presses}")


class SettingsPage(Page):
    title = "Settings"

    def __init__(self, controller):
        super().__init__(controller)
        cfg = self.c.cfg
        ch = self.c.changed
        box, form = form_group("Game")
        self.game = QLineEdit(cfg.get("game_window", ""))
        self.game.setPlaceholderText("leave empty to work in every window")
        self.game.editingFinished.connect(lambda: (cfg.__setitem__("game_window", self.game.text().strip()), ch()))
        grab = QPushButton("Use the next window I click")
        grab.clicked.connect(self.grab_window)
        self.grab_lbl = hint("")
        form.addRow("Window title", self.game)
        form.addRow("", row(grab, self.grab_lbl))
        form.addRow(hint("Cooldowns and macros only work while this window is focused, so typing in Discord "
                         "or your browser never triggers anything. Roblox's game window is called \"Roblox\"."))
        self.body.addWidget(box)

        box, form = form_group("Hotkeys")
        form.addRow("Macros on / off", KeyButton(self.c, cfg.get("toggle_key", "f6"),
                                                 lambda k: (cfg.__setitem__("toggle_key", k), ch())))
        form.addRow("Log cursor position + colour", KeyButton(self.c, cfg.get("pick_key", "f7"),
                                                              lambda k: (cfg.__setitem__("pick_key", k), ch())))
        start = QCheckBox("Start with macros ON")
        start.setChecked(cfg.get("start_active", False))
        start.toggled.connect(lambda on: (cfg.__setitem__("start_active", on), ch()))
        form.addRow("", start)
        self.body.addWidget(box)

        box, form = form_group("Screen")
        form.addRow("Monitor", spin(cfg.get("monitor", 1), 1, 8, lambda v: (cfg.__setitem__("monitor", v), ch())))
        form.addRow("Screen rule scan every", spin(cfg.get("scan_interval_ms", 50), 5, 2000,
                                                   lambda v: (cfg.__setitem__("scan_interval_ms", v), ch()), " ms", 5))
        folder = QPushButton("Open app folder")
        folder.clicked.connect(lambda: os.startfile(config.HERE))
        form.addRow("", folder)
        self.body.addWidget(box)

        icfg = cfg.setdefault("cd_icons", {"enabled": True, "x": [933, 951, 969, 987], "y": [928, 962]})
        box, form = form_group("Deepwoken cooldown bubbles", True, icfg.get("enabled", True),
                               lambda on: (icfg.__setitem__("enabled", on), ch()))
        form.addRow(hint("The small round icons under your health bar go dim while a move is on cooldown. "
                         "Bars set to a bubble (Cooldowns > Game bubble) follow them: they only start when the "
                         "game really did the move, and refill the moment the game says it's ready again."))
        self.icon_now = QLabel()
        form.addRow("Right now", self.icon_now)
        pick = QPushButton("Pick the bubbles")
        pick.setToolTip("Drag a box tightly around the 4 bubbles (only needed if your screen isn't 1920x1080).")
        pick.clicked.connect(self.pick_icons)
        form.addRow("", pick)
        self.body.addWidget(box)
        self.body.addStretch(1)
        self.grab_timer = QTimer(self, interval=100, timeout=self.poll_window)

    def pick_icons(self):
        def picked(res, img, origin):
            if res and "region" in res:
                x, y, w, h = res["region"]
                self.c.cfg["cd_icons"]["x"] = [int(x + w * (2 * i + 1) / 8) for i in range(4)]
                self.c.cfg["cd_icons"]["y"] = [y - 6, y + h + 6]
                self.c.changed()
        self.c.pick("area", picked)

    def tick(self):
        if not hasattr(self, "icon_now"):
            return
        states = getattr(self.c.engine, "icon_states", [])
        if not self.c.cfg.get("cd_icons", {}).get("enabled", True):
            self.icon_now.setText("off")
        elif not states:
            self.icon_now.setText("waiting for the game window")
        else:
            names = {"ready": "ready", "cooling": "cooling", None: "?"}
            self.icon_now.setText("   ".join(f"{i + 1}: {names[s]}" for i, s in enumerate(states)))

    def grab_window(self):
        self.own = int(self.window().winId())
        self.grab_lbl.setText("click the game window...")
        self.grab_timer.start()

    def poll_window(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd and hwnd != self.own:
            self.grab_timer.stop()
            title = engine_mod.foreground_title().strip()
            self.game.setText(title)
            self.c.cfg["game_window"] = title
            self.c.changed()
            self.grab_lbl.setText(f"set to \"{title}\"")
            self.c.show_main()


class RobloxPage(Page):
    title = "Roblox"
    subtitle = ("Works with Froststrap, Bloxstrap and Fishstrap: knows which game you're in, turns macros on in "
                "Deepwoken, and edits your FastFlags.")

    def __init__(self, controller):
        super().__init__(controller)
        rb = self.c.cfg["roblox"]
        ch = self.c.changed
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 14, 0)
        scroll.setWidget(holder)
        self.body.addWidget(scroll, 1)

        box, form = form_group("Game detection")
        self.status = QLabel()
        form.addRow("Right now", self.status)
        auto = QCheckBox("Turn macros ON when I join one of these games, OFF when I leave")
        auto.setChecked(rb.get("auto_enable", True))
        auto.toggled.connect(lambda on: (rb.__setitem__("auto_enable", on), ch()))
        form.addRow("", auto)
        self.games = QListWidget()
        self.games.setFixedHeight(90)
        form.addRow("Games", self.games)
        add = QPushButton("Add the game I'm in now")
        add.clicked.connect(self.add_current)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_game)
        form.addRow("", row(add, remove))
        self.launcher = QComboBox()
        for name, exe in fastflags.launchers():
            self.launcher.addItem(name, exe)
        self.launcher.addItem("Windows default (roblox:// link)", "link")
        saved = rb.get("launcher", "")
        if saved and self.launcher.findData(saved) >= 0:
            self.launcher.setCurrentIndex(self.launcher.findData(saved))
        self.launcher.currentIndexChanged.connect(
            lambda _: (rb.__setitem__("launcher", self.launcher.currentData()), ch(apply=False)))
        launch = QPushButton("Launch Deepwoken")
        launch.setObjectName("Primary")
        launch.clicked.connect(lambda: self.launch(config.DEEPWOKEN_PLACE))
        roblox = QPushButton("Launch Roblox")
        roblox.clicked.connect(lambda: self.launch(None))
        self.menu_btn = QPushButton("Open settings")
        self.menu_btn.clicked.connect(lambda: fastflags.open_menu(self.launcher.currentData()))
        self.menu_btn.setEnabled(self.launcher.currentData() != "link")
        self.launcher.currentIndexChanged.connect(lambda _: self.menu_btn.setEnabled(self.launcher.currentData() != "link"))
        form.addRow("Launch with", row(self.launcher, launch, roblox, self.menu_btn))
        start = QCheckBox("Start Elgansito Demolisher Macro with Windows (so it's ready whenever you play)")
        start.setChecked(rb.get("start_with_windows", False))
        start.toggled.connect(self.set_start)
        form.addRow("", start)
        lay.addWidget(box)

        box, form = form_group("FastFlags")
        form.addRow(hint("These go into the same file your bootstrapper uses, so they apply the next time Roblox "
                         "starts. Roblox ignores flags that aren't on its allowlist, so some may do nothing."))
        self.target = QComboBox()
        for label, path in fastflags.targets():
            self.target.addItem(label, path)
        saved = rb.get("fastflags_file")
        if saved and self.target.findData(saved) >= 0:
            self.target.setCurrentIndex(self.target.findData(saved))
        self.target.currentIndexChanged.connect(self.load_flags)
        form.addRow("Write to", self.target)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Flag", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(260)
        self.table.setStyleSheet("QTableWidget { background: #1b1f29; border: 1px solid #2e3445; border-radius: 7px; "
                                 "gridline-color: #262b38; } QHeaderView::section { background: #171a21; "
                                 "border: none; padding: 6px; color: #aab2c3; }")
        self.table.itemChanged.connect(lambda _: self.mark_dirty())
        form.addRow(self.table)
        add_flag = QPushButton("+ Add flag")
        add_flag.clicked.connect(lambda: self.add_flag("", ""))
        delete = QPushButton("Delete selected")
        delete.clicked.connect(self.delete_flags)
        paste = QPushButton("Paste JSON")
        paste.clicked.connect(self.paste_json)
        self.preset = QComboBox()
        for name in fastflags.PRESETS:
            self.preset.addItem(name)
        add_preset = QPushButton("Add preset")
        add_preset.clicked.connect(lambda: self.add_flag(*fastflags.PRESETS[self.preset.currentText()]))
        form.addRow("", row(add_flag, delete, paste, self.preset, add_preset))
        save = QPushButton("Save flags")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_flags)
        reload = QPushButton("Reload")
        reload.clicked.connect(self.load_flags)
        self.flag_status = hint("")
        form.addRow("", row(save, reload, self.flag_status))
        lay.addWidget(box)
        lay.addStretch(1)
        self.refresh_games()
        self.load_flags()

    def refresh_games(self):
        self.games.clear()
        for g in self.c.cfg["roblox"]["games"]:
            self.games.addItem(f"{g['name']}   (universe {g['universe_id']})")

    def add_current(self):
        eng = self.c.engine
        if not eng.universe_id:
            self.status.setText("not in a game - join it in Roblox first")
            return
        games = self.c.cfg["roblox"]["games"]
        if any(g["universe_id"] == eng.universe_id for g in games):
            return
        name, ok = QInputDialog.getText(self, "Add game", "Name for this game:", text=f"Place {eng.place_id}")
        if ok and name.strip():
            games.append({"name": name.strip(), "universe_id": eng.universe_id})
            self.c.changed()
            self.refresh_games()

    def remove_game(self):
        i = self.games.currentRow()
        if 0 <= i < len(self.c.cfg["roblox"]["games"]):
            self.c.cfg["roblox"]["games"].pop(i)
            self.c.changed()
            self.refresh_games()

    def launch(self, place_id):
        exe = self.launcher.currentData()
        try:
            if exe != "link":
                fastflags.launch(exe, place_id)
            else:
                os.startfile(f"roblox://experiences/start?placeId={place_id}" if place_id else "roblox://")
            self.c.engine.log(f"launching {'Deepwoken' if place_id else 'Roblox'} with {self.launcher.currentText()}")
        except Exception as e:
            self.status.setText(f"couldn't launch: {e}")

    def set_start(self, on):
        try:
            fastflags.set_start_with_windows(on)
            self.c.cfg["roblox"]["start_with_windows"] = on
            self.c.changed(apply=False)
        except Exception as e:
            self.status.setText(f"couldn't change startup: {e}")

    def tick(self):
        eng = self.c.engine
        if eng.universe_id:
            game = eng.current_game() or "a game not in the list"
            text = f"in <b>{game}</b> (place {eng.place_id}, universe {eng.universe_id})"
        else:
            text = "not in a Roblox game"
        self.status.setText(text + ("  -  macros ON" if eng.active else "  -  macros OFF"))

    # fast flags
    def path(self):
        return self.target.currentData()

    def load_flags(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        path = self.path()
        if not path:
            self.flag_status.setText("no Roblox install found")
            self.table.blockSignals(False)
            return
        try:
            for k, v in fastflags.load(path).items():
                self._row(k, v)
            self.flag_status.setText(f"{self.table.rowCount()} flags loaded")
        except Exception as e:
            self.flag_status.setText(f"couldn't read: {e}")
        self.table.blockSignals(False)
        self.c.cfg["roblox"]["fastflags_file"] = path
        self.c.changed(apply=False)

    def _row(self, k, v):
        i = self.table.rowCount()
        self.table.insertRow(i)
        self.table.setItem(i, 0, QTableWidgetItem(k))
        self.table.setItem(i, 1, QTableWidgetItem(v))
        return i

    def add_flag(self, k, v):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == k and k:
                self.table.item(i, 1).setText(v)
                self.table.selectRow(i)
                return
        i = self._row(k, v)
        self.table.scrollToItem(self.table.item(i, 0))
        if not k:
            self.table.editItem(self.table.item(i, 0))
        self.mark_dirty()

    def delete_flags(self):
        for i in sorted({ix.row() for ix in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(i)
        self.mark_dirty()

    def paste_json(self):
        text, ok = QInputDialog.getMultiLineText(self, "Paste FastFlags", "Paste a JSON object of flags:")
        if not ok or not text.strip():
            return
        try:
            for k, v in fastflags.parse_json(text).items():
                self.add_flag(k, v)
        except Exception as e:
            self.flag_status.setText(f"not valid JSON: {e}")

    def mark_dirty(self):
        self.flag_status.setText("unsaved changes")

    def save_flags(self):
        flags = {}
        for i in range(self.table.rowCount()):
            k = (self.table.item(i, 0).text() if self.table.item(i, 0) else "").strip()
            if k:
                flags[k] = self.table.item(i, 1).text() if self.table.item(i, 1) else ""
        try:
            fastflags.save(self.path(), flags)
            self.flag_status.setText(f"saved {len(flags)} flags - restart Roblox to apply")
        except Exception as e:
            self.flag_status.setText(f"couldn't save: {e}")


# ---- main window ----------------------------------------------------------------

class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WA_StyledBackground)
        self.win = window
        self.setFixedHeight(38)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 0, 0)
        dot = QLabel("●")
        dot.setStyleSheet("color: #3b82f6; font-size: 12pt;")
        title = QLabel("Elgansito Demolisher Macro")
        title.setObjectName("AppTitle")
        lay.addWidget(dot)
        lay.addWidget(title)
        lay.addStretch(1)
        for text, name, fn in (("—", "TitleBtn", window.showMinimized), ("✕", "CloseBtn", window.close)):
            b = QPushButton(text)
            b.setObjectName(name)
            b.setFixedHeight(38)
            b.clicked.connect(fn)
            lay.addWidget(b)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.win.windowHandle().startSystemMove()


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.c = controller
        self.setWindowTitle("Elgansito Demolisher Macro")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(1200, 760)
        self.setMinimumSize(860, 560)
        body = QWidget()
        body.setObjectName("Body")
        outer = QVBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(TitleBar(self))
        main = QHBoxLayout()
        main.setSpacing(0)
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setAttribute(Qt.WA_StyledBackground)
        side.setFixedWidth(190)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(10, 12, 10, 12)
        side_lay.setSpacing(4)
        self.stack = QStackedWidget()
        self.pages = [HomePage(controller), WidgetsPage(controller), CooldownsPage(controller),
                      MacrosPage(controller), PartyPage(controller), RulesPage(controller),
                      RobloxPage(controller), SettingsPage(controller)]
        group = QButtonGroup(self)
        self.nav = []
        for i, page in enumerate(self.pages):
            b = QPushButton(page.title)
            b.setObjectName("Nav")
            b.setCheckable(True)
            b.clicked.connect(lambda _, i=i: self.go(i))
            group.addButton(b)
            self.nav.append(b)
            side_lay.addWidget(b)
            self.stack.addWidget(page)
            if i == 0:
                b.setChecked(True)
        side_lay.addStretch(1)
        side_lay.addWidget(hint("Changes save automatically."))
        main.addWidget(side)
        main.addWidget(self.stack, 1)
        outer.addLayout(main, 1)
        grip = QSizeGrip(body)
        outer.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        self.setCentralWidget(body)
        self.go(0)

    def go(self, i):
        self.nav[i].setChecked(True)
        self.stack.setCurrentIndex(i)
        self.pages[i].shown()

    def page(self, cls):
        return next(p for p in self.pages if isinstance(p, cls))

    def closeEvent(self, e):
        self.c.quit()
        e.accept()


class Controller:
    def __init__(self):
        self.engine = engine_mod.Engine()
        self.cfg = copy.deepcopy(self.engine.cfg)
        self.engine.start()
        self.overlays = {}
        self.snapshots = {}
        self.selected_name = ""
        self.waiting_snapshot = None
        self._needs_apply = False
        self.save_timer = QTimer(singleShot=True, interval=300, timeout=self.flush)
        self.window = MainWindow(self)
        self.frame_timer = QTimer(interval=16, timeout=self.frame)
        self.frame_timer.start()
        self.ui_timer = QTimer(interval=100, timeout=self.ui_tick)
        self.ui_timer.start()
        for wid, state in list(self.cfg["widgets"].items()):
            if state.get("visible"):
                self.show_overlay(wid, save=False)

    def current_name(self):
        return self.selected_name or "picture"

    # config
    def changed(self, apply=True):
        self._needs_apply |= apply
        self.save_timer.start()

    def flush(self):
        if self._needs_apply:
            self._needs_apply = False
            self.engine.apply(self.cfg)
        try:
            config.save(self.cfg)
        except Exception as e:
            self.engine.log(f"could not save config: {e}")

    # overlays
    def valid_ids(self):
        return {wid for wid, _, _ in overlays.widget_catalog(self.cfg)}

    def overlay_visible(self, wid):
        ov = self.overlays.get(wid)
        return bool(ov and ov.isVisible())

    def show_overlay(self, wid, pos=None, save=True):
        if wid not in self.valid_ids():
            self.cfg["widgets"].pop(wid, None)
            return
        ov = self.overlays.get(wid)
        if ov is None:
            ov = overlays.make_overlay(self, wid)
            self.overlays[wid] = ov
        state = self.cfg["widgets"].setdefault(wid, {})
        if pos is not None:
            ov.move(pos)
        elif "x" in state:
            ov.move(state["x"], state["y"])
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            ov.move(screen.center() - QPoint(ov.width() // 2, ov.height() // 2))
        state["visible"] = True
        ov.show()
        if save:
            self.changed(apply=False)

    def hide_overlay(self, wid):
        ov = self.overlays.pop(wid, None)
        if ov:
            ov.close()
            ov.deleteLater()
        if wid in self.cfg["widgets"]:
            self.cfg["widgets"][wid]["visible"] = False
        self.changed(apply=False)

    def rename_overlay(self, old, new):
        state = self.cfg["widgets"].pop(old, None)
        was_visible = self.overlay_visible(old)
        ov = self.overlays.pop(old, None)
        if ov:
            ov.close()
            ov.deleteLater()
        if state:
            self.cfg["widgets"][new] = state
        if was_visible:
            QTimer.singleShot(400, lambda: self.show_overlay(new))

    def overlay_moved(self, wid, x, y):
        state = self.cfg["widgets"].setdefault(wid, {})
        state["x"], state["y"] = x, y
        self.changed(apply=False)

    def restyle_overlays(self):
        for ov in self.overlays.values():
            ov.apply_style()

    def show_main(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    # screen picking
    def pick(self, mode, callback, source=None):
        def done(result, image, origin):
            self.window.showNormal()
            self.window.raise_()
            callback(result, image, origin)

        def open_picker():
            if source:
                image, origin = detect.read_image(source[0]), source[1]
            else:
                with detect.MSS() as sct:
                    box = detect.monitor_box(sct, self.cfg.get("monitor", 1))
                    image, origin = detect.grab(sct, box), (box["left"], box["top"])
            self.picker = ScreenPicker(image, origin, mode, done)
            self.picker.show()
            self.picker.activateWindow()
            self.picker.setFocus()

        self.window.showMinimized()
        QTimer.singleShot(350, open_picker)

    # timers
    def frame(self):
        for ov in self.overlays.values():
            if ov.isVisible():
                ov.update()

    def ui_tick(self):
        page = self.window.stack.currentWidget()
        page.tick()
        while self.engine.toggled_resets:
            cd_name, r_name, on = self.engine.toggled_resets.pop(0)
            for cd in self.cfg["cooldowns"]:
                for r in cd["resets"]:
                    if cd["name"] == cd_name and r["name"] == r_name:
                        r["enabled"] = on
            self.changed(apply=False)
            if isinstance(page, CooldownsPage):
                page.shown()
        snap = self.engine.snapshot_path
        if snap:
            self.engine.snapshot_path = None
            name, path, origin = snap
            self.snapshots[name] = (path, origin)
            if self.waiting_snapshot:
                self.waiting_snapshot.snapshot_ready(name)

    def quit(self):
        self.flush()
        self.engine.stop()
        for ov in list(self.overlays.values()):
            ov.close()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    icon = config.resolve("icon.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    controller = Controller()
    controller.window.show()
    sys.exit(app.exec())


def run():
    """Entry point that writes crash.log next to the app, since the exe has no console."""
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        with open(config.resolve("crash.log"), "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        raise


if __name__ == "__main__":
    run()

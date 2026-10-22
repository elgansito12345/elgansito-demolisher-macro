"""Loading and saving config.json, with defaults for anything missing."""
import copy
import json
import os
import sys

# When packaged as an exe, keep config and templates next to the exe.
HERE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
TEMPLATE_DIR = os.path.join(HERE, "templates")

DEEPWOKEN_UNIVERSE = 1359573625
DEEPWOKEN_PLACE = 4111023553

DEFAULT_DETECT = {
    "type": "color_area",
    "region": [760, 480, 360, 360],
    "color": [255, 255, 255],
    "tolerance": 30,
    "min_fraction": 0.04,
    "point": [960, 540],
    "template": "",
    "threshold": 0.8,
}

# Tuned on a 1920x1080 recording: a landed parry's yellow spark fills ~13-16% of this
# area around the character (less when the camera is zoomed out), blocked hits only ~1.5%.
PARRY_SPARK = dict(DEFAULT_DETECT, color=[237, 209, 81], tolerance=45, min_fraction=0.025)


def new_reset(name="New reset", key="f", enabled=False, detect=None, window_ms=450):
    """Something that puts a cooldown back to ready when it's seen on screen
    shortly after pressing `key` (a parry landing, an M1 hitting...)."""
    return {"name": name, "enabled": enabled, "key": key, "toggle_key": "", "window_ms": window_ms,
            "detect": copy.deepcopy(detect or DEFAULT_DETECT)}


DEFAULTS = {
    "game_window": "Roblox",
    "toggle_key": "f6",
    "pick_key": "f7",
    "start_active": False,
    "monitor": 1,
    "scan_interval_ms": 50,
    # bar_style "flat" = plain thick parry/dodge bars (flat_width x flat_height px), "card" = with name + time
    "overlay": {"locked": False, "opacity": 0.92, "bar_style": "flat", "flat_width": 178, "flat_height": 12, "flat_outline": 1},
    "widgets": {},
    # Deepwoken's cooldown bubbles under the health bar (1920x1080): bars sync to them.
    "cd_icons": {"enabled": True, "x": [933, 951, 969, 987], "y": [928, 962]},
    # Where the Deepwoken server name is (top left info block, 1920x1080).
    "server_name": {"region": [452, 8, 188, 26]},
    # Your own health, read off your health bar (1920x1080 defaults).
    "my_hp": {
        "region": [722, 880, 476, 50],
        # raw bar fill -> real %, measured: the fill reads 0.924 when the game says 91%
        "calibration": [[0.924, 0.91]],
    },
    # Share your HP with friends who run Elgansito Demolisher Macro with the same party code.
    "party": {
        "enabled": False,
        "username": "",
        "code": "",
        "friends": [],
        "broker": "broker.emqx.io",
        "port": 8883,
    },
    # Press Deepwoken's Z / X / C / V prompts when they show up (never the teal fakes).
    "prompts": {
        "enabled": False,
        "region": [480, 150, 960, 700],
        "threshold": 0.82,
        "delay_ms": 0,
    },
    "roblox": {
        "auto_enable": True,
        "games": [{"name": "Deepwoken", "universe_id": DEEPWOKEN_UNIVERSE}],
        "fastflags_file": "",
        "start_with_windows": False,
    },
    "cooldowns": [
        {
            "name": "Dodge",
            "key": "q",
            "cooldown_ms": 2000,
            "color": "#69b9e8",
            "icon_slot": 1,
            "cancel": {"enabled": True, "key": "mouse_right", "window_ms": 350, "cooldown_ms": 0, "max_refunds": 1},
            "resets": [new_reset("Blade Dancer (M1 hit)", "mouse_left", window_ms=350)],
        },
        {
            "name": "Parry",
            "key": "f",
            "cooldown_ms": 1200,
            "color": "#3bb967",
            "icon_slot": 2,
            "cancel": {"enabled": False, "key": "mouse_right", "window_ms": 350, "cooldown_ms": 0, "max_refunds": 1},
            "resets": [new_reset("Parry landed", "f", True, PARRY_SPARK)],
        },
    ],
    "macros": [
        {
            "name": "Roll parry",
            "enabled": True,
            "hotkey": "t",
            "block_key": False,
            "mode": "once",
            "interval_ms": 100,
            "steps": [
                {"action": "down", "key": "ctrl"},
                {"action": "wait", "ms": 15},
                {"action": "tap", "key": "q", "ms": 25},
                {"action": "wait", "ms": 30},
                {"action": "click", "button": "right", "ms": 25},
                {"action": "up", "key": "ctrl"},
            ],
        },
        {
            "name": "Feint parry",
            "enabled": True,
            "hotkey": "f",
            "block_key": True,
            "mode": "once",
            "interval_ms": 100,
            "steps": [
                {"action": "click", "button": "right", "ms": 4},
                {"action": "wait", "ms": 4},
                {"action": "down", "key": "f"},
                {"action": "wait_release"},
                {"action": "up", "key": "f"},
            ],
        },
    ],
    "rules": [],
}


def new_cooldown(name="New cooldown"):
    cd = copy.deepcopy(DEFAULTS["cooldowns"][1])
    cd.update(name=name, key="e", color="#a78bfa", resets=[], icon_slot=0)
    return cd


def new_macro(name="New macro"):
    return {"name": name, "enabled": True, "hotkey": "", "block_key": False, "mode": "once", "interval_ms": 100,
            "steps": [{"action": "tap", "key": "e", "ms": 25}]}


def new_member(name="Friend"):
    return {"name": name, "region": None}


def new_rule(name="New screen rule"):
    detect = copy.deepcopy(DEFAULT_DETECT)
    detect.update(type="image", region=[860, 440, 200, 200])
    return {"name": name, "enabled": True, "detect": detect, "trigger": "on_appear", "cooldown_ms": 500,
            "action": {"type": "none", "key": "space", "button": "left", "at": "match", "point": [960, 540],
                       "return_mouse": True, "ms": 30}}


def _fill(cfg, defaults):
    for key, value in defaults.items():
        if key not in cfg:
            cfg[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(cfg[key], dict):
            _fill(cfg[key], value)


def _migrate(cfg):
    # Older configs used "combos" and flat rules.
    if "combos" in cfg and "macros" not in cfg:
        cfg.pop("combos")
        cfg["macros"] = copy.deepcopy(DEFAULTS["macros"])
        cfg["rules"] = [r for r in cfg.get("rules", []) if "detect" in r]
        for cd in cfg.get("cooldowns", []):
            cd.setdefault("cancel", {}).setdefault("enabled", bool(cd["cancel"].get("key")))
    cfg.pop("capture_size", None)
    # One "reset_detect" per cooldown became a list of "resets"; use the tuned defaults.
    defaults = {cd["name"]: cd for cd in DEFAULTS["cooldowns"]}
    for cd in cfg.get("cooldowns", []):
        old = cd.pop("reset_detect", None)
        if "resets" in cd:
            continue
        if cd["name"] in defaults:
            cd["resets"] = copy.deepcopy(defaults[cd["name"]]["resets"])
        elif old and old.get("enabled"):
            detect = {k: v for k, v in old.items() if k not in ("enabled", "window_ms")}
            cd["resets"] = [new_reset(f"{cd['name']} lands", cd["key"], True, detect, old.get("window_ms", 450))]
    # Party HP used to come from a Matcha script's file; it's now shared between Elgansito Demolisher Macro users.
    party = cfg.get("party")
    if isinstance(party, dict) and ("names_file" in party or "members" in party):
        cfg["party"] = copy.deepcopy(DEFAULTS["party"])
    # Parry spark threshold lowered from 4% so zoomed-out landings still count.
    if not cfg.get("_parry_spark_v2"):
        cfg["_parry_spark_v2"] = True
        for cd in cfg.get("cooldowns", []):
            for r in cd.get("resets", []):
                d = r.get("detect", {})
                if d.get("color") == PARRY_SPARK["color"] and d.get("min_fraction") == 0.04:
                    d["min_fraction"] = PARRY_SPARK["min_fraction"]
    # Sync Dodge / Parry with the game's cooldown bubbles (roll = 1st, parry = 2nd).
    if not cfg.get("_icon_slots_v1"):
        cfg["_icon_slots_v1"] = True
        for cd in cfg.get("cooldowns", []):
            cd.setdefault("icon_slot", {"Dodge": 1, "Parry": 2}.get(cd.get("name"), 0))
    # Flat bars: switch the old default colours to the light blue / green look.
    if not cfg.get("_flat_bars_v1"):
        cfg["_flat_bars_v1"] = True
        new = {"#4aa3ff": "#69b9e8", "#ffb347": "#3bb967"}
        for cd in cfg.get("cooldowns", []):
            cd["color"] = new.get(cd.get("color", "").lower(), cd.get("color"))
    # Add the feint-parry macro once.
    if not cfg.get("_added_feint_parry"):
        cfg["_added_feint_parry"] = True
        names = {m.get("name") for m in cfg.get("macros", [])}
        if "Feint parry" not in names:
            cfg.setdefault("macros", []).append(copy.deepcopy(DEFAULTS["macros"][1]))


def normalise(cfg):
    _migrate(cfg)
    _fill(cfg, {k: v for k, v in DEFAULTS.items() if k not in ("cooldowns", "macros", "rules")})
    for cd in cfg.setdefault("cooldowns", []):
        _fill(cd, new_cooldown())
        for r in cd["resets"]:
            _fill(r, new_reset())
    for m in cfg.setdefault("macros", []):
        _fill(m, new_macro())
    for r in cfg.setdefault("rules", []):
        _fill(r, new_rule())
    return cfg


def load():
    if not os.path.exists(CONFIG_PATH):
        return normalise(copy.deepcopy(DEFAULTS))
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return normalise(json.load(f))


def save(cfg):
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


def resolve(path):
    return path if os.path.isabs(path) else os.path.join(HERE, path)

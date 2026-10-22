# Elgansito Demolisher Macro

A free, open-source helper for Deepwoken (Roblox): cooldown bars for dodge and
parry that follow the game's own cooldown icons, macros you build from simple
steps, and a Party HP overlay where friends running the app see each other's
health, server, region and PvP combat.

Everything is plain Python in this repo, so you can read exactly what it does.
It is **not** a RAT, keylogger or spyware: see [What it can see and send](#what-it-can-see-and-send).

## Download

1. Go to **Releases** (right side of this page) and download
   `ElgansitoDemolisherMacro-windows.zip`.
2. Unzip it anywhere and run `ElgansitoDemolisherMacro.exe`. No install, no Python needed.
3. Windows SmartScreen may warn because the exe isn't code-signed: click
   **More info → Run anyway**, or build it yourself from source (below).

Settings are saved in `config.json` next to the exe.

## What it does

- **Cooldown bars (Parry / Dodge):** thick flat bars you drag anywhere on screen.
  They read Deepwoken's cooldown bubbles under your health bar, so they only start
  when the game really did the move, refill the moment it's ready again (landed
  parries, roll cancels, Blade Dancer), and learn the real cooldown length.
- **Macros:** pick a hotkey and add steps (press key, hold key, click, wait...).
  Built in: **T = Roll parry** and **F = Feint parry** (right click → F).
  Toggle all macros with **F6**. Macros only work while the Roblox window is focused.
- **Party HP:** each player's app reads their own health bar (and the "N% HEALTH"
  text under 14%), Deepwoken server name, region, and the red PvP danger skull
  (with how many players). Friends with the same party code see each other as bars;
  rows pulse red under 50% and show **PVP xN** when someone's in combat.
- **Z / X / C / V prompts:** pressed for you when they appear (never the teal fakes).
- **Roblox:** turns macros on when you join Deepwoken, launches it through your
  bootstrapper (Froststrap / Bloxstrap / Fishstrap), and has a FastFlag editor.
- **Screen rules:** react to a picture or colour on screen with a key press or click.

Defaults are for a 1920x1080 screen. On other sizes, use the **Pick area** buttons.

## Party HP setup

Everyone in the party:

1. Party HP page → tick **Share with friends**.
2. Type your **Roblox username**.
3. One person presses **New code** → **Copy** and sends the code to the others; everyone pastes the same code.
4. Optional: list friends' usernames, comma separated, to only show those people.
5. Press **Show Party HP on screen**.

## What it can see and send

| What | Why | Leaves your PC? |
| --- | --- | --- |
| Small areas of your screen (health bar, cooldown bubbles, top HUD text, prompt area) | to read HP, cooldowns, server/region, PvP, prompts | No |
| Keyboard and mouse presses | hotkeys, macros and cooldown timing; nothing is recorded or saved | No |
| Roblox's own log file (`%LOCALAPPDATA%\Roblox\logs`) | to know which game/server you're in | No (only a one-way hash of the server id, see below) |
| Your Roblox username, HP %, server name, region, PvP state, server-id hash | Party HP | **Only if you turn on Share with friends**: encrypted with your party code and sent through a public MQTT relay (`broker.emqx.io`); only people with the code can read it |
| FastFlags file | only when you press **Save flags** | No |
| Windows startup entry | only if you tick **Start with Windows** | No |

There's no other network traffic, no telemetry, no auto-updater, and no reading of
Roblox's memory. Text on screen is read with Windows' built-in OCR, offline.

## Build from source

Needs Python 3.12 on Windows.

```
pip install -r requirements.txt
python app.py
```

Build the exe:

```
pip install pyinstaller
pyinstaller --noconfirm --windowed --name ElgansitoDemolisherMacro --icon icon.ico --collect-all winrt --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 app.py
```

Then copy `templates/` next to the exe in `dist/ElgansitoDemolisherMacro/`.

## Files

| File | What |
| --- | --- |
| `app.py` | the control panel (start here) |
| `overlays.py` | the drag-anywhere overlays |
| `engine.py` | input hooks, cooldowns, macros, screen reading loops |
| `combat.py` | cooldown, macro and rule logic |
| `icons.py` | reads the game's cooldown bubbles |
| `hp.py` | reads your health bar / health text |
| `hud.py`, `servername.py` | reads region, PvP danger and server name (Windows OCR) |
| `party.py` | encrypted HP sharing with friends |
| `prompts.py` | Z / X / C / V prompt finder |
| `detect.py` | screen capture and matching |
| `sendinput.py` | sends keys and clicks the way games read them |
| `fastflags.py` | FastFlags, launching Roblox, start with Windows |
| `config.py` | settings and defaults |
| `templates/prompts/` | pictures of the game's key prompts |

## License

MIT, see [LICENSE](LICENSE). Not affiliated with Roblox or Deepwoken. Use at your own risk.

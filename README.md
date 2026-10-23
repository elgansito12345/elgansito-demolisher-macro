# Elgansito Demolisher Macro

A free, open-source helper for Deepwoken (Roblox): cooldown bars for dodge and
parry that follow the game's own cooldown icons, macros you build from simple
steps, and a Party HP overlay where friends running the app see each other's
health, server, region and PvP combat.

Everything is plain Python in this repo, so you can read exactly what it does.
It is **not** a RAT, keylogger or spyware: see [What it can see and send](#what-it-can-see-and-send).

## Download

1. Go to **Releases** (right side of this page) and download
   `ElgansitoDemolisherMacro-windows.zip` (everything) or `ElgansitoLite-windows.zip` (lighter, see below).
2. Unzip it anywhere and run the exe. No install, no Python needed.
3. Windows SmartScreen may warn because the exe isn't code-signed: click
   **More info → Run anyway**.

### If Windows Security deletes or blocks the exe

New, unsigned apps that read the keyboard and send key presses (like any macro tool)
sometimes get flagged as "potentially unwanted" by reputation alone. It's a false
positive; the whole source is in this repo. Either:

- **Run it without the exe:** on this page click **Code → Download ZIP**, unzip it,
  and double-click **`Run from source.bat`**. The first time it installs Python 3.12
  and the libraries; after that it just starts the app.
- **Or allow it:** Windows Security → Virus & threat protection → Protection history →
  the blocked item → **Actions → Allow on device**, then unzip again.

Settings are saved in `%APPDATA%\ElgansitoDemolisher`, so updating or re-unzipping keeps them.

## What's new in v2

- **Cyberpunk look:** new yellow/cyan UI, your own **profile picture** (click it), name and tagline,
  and an optional **background image** with a dim slider (Settings → Interface).
- **Bar styles** (Overlays): *flat*, *neon* (angled cyber bar), *card*, or *image*, where you import
  your own **empty** and **full** bar pictures (like a Cyberpunk bar) and it fills between them.
  Optional **bar text** such as `PARRY READY` (`{NAME}` and `{STATUS}` work). All of it is off unless you
  pick it, so the plain bar stays the fastest.
- **Line up bars** puts every bar in a neat column; bars also **snap** to each other when dragged close.
- **Notifications:** toasts in the top-right corner with **your own sound** (pick any mp3/wav) and image,
  for macros arming, Builder talents and a friend dropping low.
- **Hide hotkey (F8)** hides every overlay and the window; press again to bring them back.
- **Spam F:** hold mouse side button 2 to spam F (interval adjustable in Macros).
- **BUILDER 101:** paste your `deepwoken.co` builder link, it lists the build's talents in an overlay
  (top right) and, with *watch* on, reads the talent cards on screen and plays your sound when one in
  your build is offered. Tick talents off as you get them.
- **Music:** play your own music files with a playlist, loop and shuffle, plus play/pause/next
  buttons that also control Spotify. (No YouTube streaming and no songs are bundled, for copyright.)
- **FastFlag presets:** *Elgansito – Bloxstrap basis* (68 flags) and *Elgansito – Froststrap* (256 flags),
  loaded into the table with one click; optional **merge before launch**. Download buttons for
  **Froststrap v1.5.0** and **Bloxstrap** (official GitHub releases).
- **Performance** setting: *light* / *balanced* / *max* changes how often the screen is read and how
  smooth the overlays draw.

### Elgansito Lite

`ElgansitoLite.exe` is the same app with only the core: cooldown bars (with the bubbles), macros,
Spam F, overlays, profiles, the Roblox page and FastFlags. It leaves out Party HP, key prompts, Builder 101,
screen rules and music, so it uses the least CPU and memory. It shares settings and profiles with the full app.

## What it does

- **Cooldown bars (Parry / Dodge):** thick flat bars you drag anywhere on screen.
  They read Deepwoken's cooldown bubbles under your health bar, so they only start
  when the game really did the move, refill the moment it's ready again (landed
  parries, roll cancels, Blade Dancer), and learn the real cooldown length.
- **Macros:** pick a hotkey and add steps (press key, hold key, click, wait...).
  Built in: **T = Roll uppercut** (hold Ctrl → wait 80 ms → Q 30 ms → wait 30 ms → right click 25 ms → release Ctrl)
  and **C = roll m1** (Q 125 ms → right click 75 ms → left click 25 ms).
  **Mouse side button 2 = Spam F.** Toggle all macros with **F6**. Macros only work while the Roblox window is focused.
- **Party HP:** (size and bar thickness in Overlays) each player's app reads their own health bar (and the "N% HEALTH"
  text under 14%), Deepwoken server name, region, and the red PvP danger skull
  (with how many players). Friends with the same party code see each other as bars;
  rows pulse red under 50% and show **PVP xN** when someone's in combat.
- **Z / X / C / V prompts:** pressed for you when they appear (never the teal fakes).
- **Roblox:** turns macros on when you join Deepwoken, launches it through your
  bootstrapper (Froststrap / Bloxstrap / Fishstrap), and has a FastFlag editor.
  **Copy all** puts your flags on the clipboard to send to a friend, who presses **Paste JSON**
  (or use Save to file / Load from file).
- **Screen rules:** react to a picture or colour on screen with a key press or click.

Defaults are for a 1920x1080 screen. On other sizes, use the **Pick area** buttons: the picker
opens on the monitor the game is on and works with two monitors and Windows scaling (2K at 125%, 150%...).

Clicks have a soft sound and a small animation; both can be turned off in Settings → Interface.

## Profiles

Save different setups and switch between them, for example *PvP* and *Grinding*:

- Bottom of the sidebar: **+ Save as new profile** saves everything you have now under a name,
  and the dropdown switches between profiles instantly (bars, macros, overlays, party settings).
- The profile you're on saves itself as you change things.
- **Settings → Profiles** to switch, make a copy, rename or delete.
- **Settings → Your settings → Export / Import** to back up or share one.

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
| FastFlags file | only when you press **Save flags** (or launch with *merge before launch* on) | No |
| Your deepwoken.co build page | only when you press **Load build** | It downloads that page, nothing is sent |
| Spotify window title | to show the song in the Music page | No |
| Windows startup entry | only if you tick **Start with Windows** | No |

There's no other network traffic, no telemetry, no auto-updater, and no reading of
Roblox's memory. Text on screen is read with Windows' built-in OCR, offline.

## Build from source

Needs Python 3.12 on Windows.

Double-click `Run from source.bat`, or:

```
pip install -r requirements.txt
python app.py
```

Build the exe:

```
pip install pyinstaller
pyinstaller --noconfirm --windowed --name ElgansitoDemolisherMacro --icon icon.ico --collect-all winrt --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 app.py
```

Lite: same command with `--name ElgansitoLite lite.py` instead of `--name ElgansitoDemolisherMacro ... app.py`.

Then copy `templates/` and `assets/` next to each exe in `dist/<name>/`.

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
| `config.py` | settings, profiles and defaults |
| `lite.py` | starts Elgansito Lite |
| `builder.py` | reads deepwoken.co builds and matches talents on screen |
| `notify.py`, `audio.py` | toasts, your notification sound and the music player |
| `uifx.py` | click sound and animations |
| `assets/fastflags/` | the Elgansito FastFlag presets |
| `Run from source.bat` | runs the app from these files, no exe |
| `templates/prompts/` | pictures of the game's key prompts |

## Credits

- Deepwoken banner art: *Immortalis* by @MelancholyVal (signed on the image).
- App picture: an anime screenshot. Both pictures belong to their creators and are only used
  as decoration; ask and they'll be swapped out.

## License

MIT, see [LICENSE](LICENSE). Not affiliated with Roblox or Deepwoken. Use at your own risk.

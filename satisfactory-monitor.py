#!/usr/bin/env python3
"""
Satisfactory Dedicated Server Monitor
Queries the server's HTTPS API and displays state in a formatted matrix.

Config file (~/.config/satisfactory-monitor/config.json):
  {
    "host": "192.168.1.100",
    "port": 7777,
    "token": "your_api_token_here"
  }

Command-line arguments always override config file values.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import ssl
import time
from datetime import timedelta
from pathlib import Path


# ── Config file ───────────────────────────────────────────────────────────────

CONFIG_DIR  = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "satisfactory-monitor"
CONFIG_FILE = CONFIG_DIR / "config.json"

CONFIG_KEYS = ("host", "port", "token")


def load_config() -> dict:
    """Load config from file, returning an empty dict if not found."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open() as f:
            data = json.load(f)
        return {k: data[k] for k in CONFIG_KEYS if k in data}
    except (json.JSONDecodeError, OSError) as e:
        print(f"{YELLOW}⚠ Could not read config file ({CONFIG_FILE}): {e}{RESET}", file=sys.stderr)
        return {}


def save_config(cfg: dict) -> None:
    """Save the given keys to the config file, merging with existing content."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open() as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    existing.update(cfg)
    # Remove keys explicitly set to None
    existing = {k: v for k, v in existing.items() if v is not None}
    with CONFIG_FILE.open("w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")
    CONFIG_FILE.chmod(0o600)   # token is sensitive
    print(f"{GREEN}✓ Config saved to {CONFIG_FILE}{RESET}")


def print_config(cfg: dict) -> None:
    print(f"\n  Config file: {CONFIG_FILE}")
    if not cfg:
        print(f"  {DIM}(no config file found){RESET}\n")
        return
    for k in CONFIG_KEYS:
        val = cfg.get(k, f"{DIM}(not set){RESET}")
        if k == "token" and val and val != f"{DIM}(not set){RESET}":
            val = val[:8] + "…" + val[-4:] if len(str(val)) > 14 else "****"
        print(f"  {DIM}{k:<8}{RESET} {val}")
    print()


# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
WHITE  = "\033[97m"
BG_DARK = "\033[48;5;235m"


def colour_health(tick_rate: float) -> str:
    if tick_rate >= 25:
        return GREEN
    elif tick_rate >= 10:
        return YELLOW
    return RED


def format_duration(seconds: int) -> str:
    td = timedelta(seconds=seconds)
    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def shorten_schematic(path: str) -> str:
    """Extract a human-readable name from a UE asset path."""
    if not path:
        return "None"
    # e.g. '/Game/.../Schematic_6-7.Schematic_6-7_C'  →  'Schematic_6-7'
    tail = path.split("'")[-2] if "'" in path else path
    name = tail.split(".")[-1].replace("_C", "")
    return name or path


def shorten_game_phase(path: str) -> str:
    if not path or path == "None":
        return "None"
    # '/Game/.../GP_Project_Assembly_Phase_1.GP_Project_Assembly_Phase_1'
    tail = path.split("'")[-2] if "'" in path else path
    name = tail.split(".")[-1]
    # GP_Project_Assembly_Phase_1 → Phase 1
    name = name.replace("GP_Project_Assembly_", "").replace("_", " ").title()
    return name or path


# ── API call ──────────────────────────────────────────────────────────────────

def query_server_state(host: str, port: int, token: str) -> dict:
    url = f"https://{host}:{port}/api/v1"
    payload = json.dumps({"function": "QueryServerState"}).encode("utf-8")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # self-signed certs are common

    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        body = resp.read().decode("utf-8")

    result = json.loads(body)
    if "errorCode" in result:
        raise RuntimeError(f"API error [{result['errorCode']}]: {result.get('errorMessage', '')}")

    return result["data"]["serverGameState"]


# ── Rendering ─────────────────────────────────────────────────────────────────

def draw_matrix(state: dict, host: str, port: int) -> None:
    W = 58   # inner content width

    def rule(left="╔", mid="═", right="╗"):
        print(f"{CYAN}{left}{mid * (W + 2)}{right}{RESET}")

    def divider(left="╠", mid="═", right="╣"):
        print(f"{CYAN}{left}{mid * (W + 2)}{right}{RESET}")

    def row(label: str, value: str, value_colour: str = WHITE):
        label_w = 24
        val_w = W - label_w - 3   # " │ " separator
        label_fmt = f"{DIM}{label:<{label_w}}{RESET}"
        val_str = str(value)
        # Truncate long values
        if len(val_str) > val_w:
            val_str = val_str[: val_w - 1] + "…"
        val_fmt = f"{value_colour}{val_str:<{val_w}}{RESET}"
        print(f"{CYAN}║{RESET} {label_fmt} {CYAN}│{RESET} {val_fmt} {CYAN}║{RESET}")

    def blank():
        print(f"{CYAN}║{RESET}{' ' * (W + 2)}{CYAN}║{RESET}")

    def header(title: str):
        pad = W + 2 - len(title)
        lpad = pad // 2
        rpad = pad - lpad
        print(f"{CYAN}║{RESET}{' ' * lpad}{BOLD}{CYAN}{title}{RESET}{' ' * rpad}{CYAN}║{RESET}")

    # ── Derived values ──
    is_running   = state.get("isGameRunning", False)
    is_paused    = state.get("isGamePaused", False)
    tick_rate    = state.get("averageTickRate", 0.0)
    players      = state.get("numConnectedPlayers", 0)
    player_limit = state.get("playerLimit", 0)
    duration     = state.get("totalGameDuration", 0)

    status_colour = GREEN if is_running and not is_paused else (YELLOW if is_running else RED)
    status_text   = ("Running" if is_running and not is_paused
                     else "Paused" if is_paused else "Idle / No Session")

    player_colour = GREEN if players > 0 else DIM
    tick_colour   = colour_health(tick_rate)

    phase         = shorten_game_phase(state.get("gamePhase", "None"))
    schematic     = shorten_schematic(state.get("activeSchematic", ""))
    session_name  = state.get("activeSessionName", "—")
    auto_session  = state.get("autoLoadSessionName", "—")
    tech_tier     = state.get("techTier", "—")

    # ── Draw ──
    print()
    rule("╔", "═", "╗")
    header("SATISFACTORY  SERVER  MONITOR")
    header(f"{host}:{port}")
    divider()
    blank()

    row("Status",            status_text,              status_colour)
    row("Session",           session_name,             WHITE)
    row("Auto-load Session", auto_session,             DIM)
    blank()
    divider("╠", "─", "╣")
    blank()

    row("Players Connected", f"{players} / {player_limit}",    player_colour)
    row("Average Tick Rate", f"{tick_rate:.1f} tps",            tick_colour)
    row("Tech Tier",         str(tech_tier),                    CYAN)
    row("Game Phase",        phase,                             WHITE)
    row("Active Milestone",  schematic,                         WHITE)
    blank()
    divider("╠", "─", "╣")
    blank()

    row("Game Running",      "Yes" if is_running else "No",     GREEN if is_running else RED)
    row("Game Paused",       "Yes" if is_paused  else "No",     YELLOW if is_paused else DIM)
    row("Total Play Time",   format_duration(duration),         WHITE)
    blank()
    rule("╚", "═", "╝")
    print(f"  {DIM}Refreshed at {time.strftime('%H:%M:%S')}{RESET}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Monitor a Satisfactory Dedicated Server via its HTTPS API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"Config file: {CONFIG_FILE}\n\n"
            "  Save connection settings so you don't have to retype them:\n"
            "    %(prog)s 192.168.1.100 -t MY_TOKEN --save\n"
            "    %(prog)s          # uses saved host/port/token automatically\n\n"
            "  Use --config to view current config file contents.\n"
            "  Use --clear-token to remove a saved token from the config file.\n"
        ),
    )

    p.add_argument("host",  nargs="?",  default=None,
                   help="Server hostname or IP (can be saved in config)")
    p.add_argument("-p", "--port",  type=int, default=None,
                   help="API port (default: 7777)")
    p.add_argument("-t", "--token", default=None,
                   help="Bearer token for authentication")
    p.add_argument("-w", "--watch", type=int, metavar="SECS", default=0,
                   help="Poll interval in seconds (0 = single query)")

    cfg_group = p.add_argument_group("config management")
    cfg_group.add_argument("--save",        action="store_true",
                           help="Save host, port, and/or token to the config file")
    cfg_group.add_argument("--config",      action="store_true",
                           help="Show current config file contents and exit")
    cfg_group.add_argument("--clear-token", action="store_true",
                           help="Remove the saved token from the config file")

    return p.parse_args()


def main():
    args = parse_args()

    # Load persisted config first; CLI args override
    cfg = load_config()

    # ── Config management sub-commands ──
    if args.config:
        print_config(cfg)
        return

    if args.clear_token:
        cfg.pop("token", None)
        save_config(cfg)
        return

    # Resolve final values: CLI > config file > defaults
    host  = args.host  or cfg.get("host")
    port  = args.port  or cfg.get("port")  or 7777
    token = args.token or cfg.get("token") or ""

    if not host:
        print(
            f"{RED}✗ No host specified. "
            f"Pass a hostname/IP or run with --save to store one.{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.save:
        to_save = {"host": host, "port": port}
        if args.token:          # only persist a token when explicitly supplied
            to_save["token"] = args.token
        save_config(to_save)

    def once():
        try:
            state = query_server_state(host, port, token)
            draw_matrix(state, host, port)
        except urllib.error.URLError as e:
            print(f"{RED}✗ Could not connect to {host}:{port} — {e.reason}{RESET}", file=sys.stderr)
            sys.exit(1)
        except RuntimeError as e:
            print(f"{RED}✗ {e}{RESET}", file=sys.stderr)
            sys.exit(1)

    if args.watch > 0:
        try:
            while True:
                print("\033[2J\033[H", end="")
                once()
                print(f"  {DIM}Next refresh in {args.watch}s — Ctrl+C to quit{RESET}\n")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print(f"\n{DIM}Monitor stopped.{RESET}")
    else:
        once()


if __name__ == "__main__":
    main()

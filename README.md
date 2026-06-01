# Satisfactory Server Monitor

A zero-dependency command-line tool for monitoring a [Satisfactory](https://www.satisfactorygame.com/) Dedicated Server via its HTTPS API. Displays live server state in a clean terminal matrix.

```
╔══════════════════════════════════════════════════════════════╗
║           SATISFACTORY  SERVER  MONITOR                      ║
║                  192.168.1.100:7777                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║ Status                   │ Running                           ║
║ Session                  │ MyFactory                         ║
║ Auto-load Session        │ MyFactory                         ║
║                                                              ║
╠──────────────────────────────────────────────────────────────╣
║                                                              ║
║ Players Connected        │ 2 / 4                             ║
║ Average Tick Rate        │ 30.0 tps                          ║
║ Tech Tier                │ 6                                 ║
║ Game Phase               │ Phase 1                           ║
║ Active Milestone         │ Schematic_6-7                     ║
║                                                              ║
╠──────────────────────────────────────────────────────────────╣
║                                                              ║
║ Game Running             │ Yes                               ║
║ Game Paused              │ No                                ║
║ Total Play Time          │ 4d 12h 33m 7s                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
  Refreshed at 14:22:05
```

## Features

- Displays all fields from the `QueryServerState` API response
- Colour-coded tick rate health (green / yellow / red)
- Human-readable game phase, milestone, and play duration
- Live watch mode with automatic refresh
- Config file support — save your host, port, and token once
- No third-party dependencies — pure Python 3 standard library

## Requirements

- Python 3.7+
- A running Satisfactory Dedicated Server with its HTTPS API accessible

## Installation

Clone or download `satisfactory-monitor.py` and make it executable:

```bash
chmod +x satisfactory-monitor.py
```

Optionally move it somewhere on your `PATH`:

```bash
mv satisfactory-monitor.py ~/.local/bin/satisfactory-monitor
```

## Authentication

Most API calls require a Bearer token. Generate one from the Dedicated Server console:

```
server.GenerateAPIToken
```

Copy the output — you'll pass it via `-t` or save it to the config file.

> If your server is running locally with `FG.DedicatedServer.AllowInsecureLocalAccess=1` set, the token can be omitted.

## Usage

### One-shot query

```bash
python satisfactory-monitor.py 192.168.1.100
python satisfactory-monitor.py 192.168.1.100 -p 7777 -t YOUR_TOKEN
```

### Live watch mode

Refresh every N seconds (Ctrl+C to stop):

```bash
python satisfactory-monitor.py 192.168.1.100 -w 10
```

### All options

```
positional arguments:
  host                  Server hostname or IP (can be saved in config)

options:
  -p, --port SECS       API port (default: 7777)
  -t, --token TOKEN     Bearer token for authentication
  -w, --watch SECS      Poll interval in seconds (0 = single query)

config management:
  --save                Save host, port, and/or token to the config file
  --config              Show current config file contents and exit
  --clear-token         Remove the saved token from the config file
```

## Config File

Connection settings can be persisted so you don't need to pass them every time.

**Save your settings:**

```bash
python satisfactory-monitor.py 192.168.1.100 -p 7777 -t YOUR_TOKEN --save
```

**Then run with no arguments:**

```bash
python satisfactory-monitor.py
```

**Config file location:** `~/.config/satisfactory-monitor/config.json`
(respects `$XDG_CONFIG_HOME` if set)

The file is saved with `chmod 600` permissions since it may contain your API token.

**Example config file:**

```json
{
  "host": "192.168.1.100",
  "port": 7777,
  "token": "your_api_token_here"
}
```

### Config management commands

| Command | Description |
|---|---|
| `--save` | Save the current host, port, and token (if `-t` was passed) |
| `--config` | Print the current config file and exit |
| `--clear-token` | Remove the saved token from the config file |

CLI flags always override config file values, so you can always connect to a different server without changing your saved config:

```bash
python satisfactory-monitor.py other-server.local -t OTHER_TOKEN
```

## Self-Signed Certificates

Satisfactory Dedicated Servers use a self-signed TLS certificate by default. The tool handles this automatically by disabling certificate verification, which is standard practice for this use case.

## API Reference

This tool uses the `QueryServerState` function from the [Satisfactory Dedicated Server HTTPS API](https://satisfactory.wiki.gg/wiki/Dedicated_servers/HTTPS_API).

## License

MIT

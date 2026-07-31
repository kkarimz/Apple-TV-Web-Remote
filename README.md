# Apple TV Web Remote

LAN web remote for office Apple TV, hosted on the Dell at **http://10.0.0.188:8083**.

Uses [pyatv](https://pyatv.dev/) Companion protocol for D-pad, select, menu, home, play/pause, and volume.

## Features

- Scan & pick an Apple TV on the LAN
- One-time PIN pairing (code shown on the TV)
- Remote: directions, OK, Menu, Home, TV/top menu, volume, play/pause
- Keyboard: arrow keys, Enter, Esc, Space
- Auto-reconnect after restart when already paired

## Layout

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI + pyatv |
| `static/index.html` | Remote UI |
| `settings.json` | Selected device (gitignored) |
| `pyatv.conf` | Pairing credentials (gitignored) |
| `systemd/atv-web.service` | User systemd unit |

## Deploy (Dell)

```bash
# code lives in /home/kais/atv-web with its own .venv
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user restart atv-web.service
```

## Pairing

1. Open http://10.0.0.188:8083  
2. Scan → select **Office** (or the correct Apple TV)  
3. Start pairing → enter PIN from the TV  
4. Connect if needed  

Volume works when Apple TV controls the display/speakers via CEC/eARC.

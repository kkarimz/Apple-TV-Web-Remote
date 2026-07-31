# Apple TV Web Remote

LAN web remote for Apple TV, accessible from any browser on your network.

Uses [pyatv](https://pyatv.dev/) Companion protocol for D-pad, apps, power, and text input.

## Features

- Scan & pick an Apple TV on the LAN
- One-time PIN pairing (code shown on the TV)
- Remote: directions, OK, Menu, Home, TV/top menu, volume, play/pause
- YouTube one-tap launch
- Text input for on-TV search keyboards
- Sleep / Wake
- Auto-reconnect on open when already paired
- Installable PWA (Add to Home Screen)
- Desktop keyboard: arrow keys, Enter, Esc, Space

## Layout

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI + pyatv |
| `static/index.html` | Remote UI |
| `settings.json` | Selected device (gitignored) |
| `pyatv.conf` | Pairing credentials (gitignored) |
| `systemd/atv-web.service` | User systemd unit |

## Deploy

```bash
# Example systemd restart command (adjust paths in your .service file)
systemctl --user restart atv-web.service
```

## Pairing

1. Open the web interface (e.g. `http://<your-server-ip>:8888`)
2. Scan → select your Apple TV
3. Start pairing → enter PIN from the TV  
4. Connect if needed  

Volume works when Apple TV controls the display/speakers via CEC/eARC.

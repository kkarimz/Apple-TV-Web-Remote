# Dell Server — Master Reference

**IP:** 10.0.0.188 | **User:** kais | **SSH alias:** `dell-server`
**OS:** Ubuntu 26.04 LTS | **Hardware:** Dell desktop, 467GB disk, 8-core CPU

This is the master index for everything running on this server.
Each section links to a dedicated doc with full details.

---

## 1. Lofi Player (24/7)
**Doc:** `/home/kais/SETUP.md`

A 24/7 lofi music player that streams Lofi Girl's live YouTube feed over Bluetooth to a Wuzhi Audio speaker. Fully automated — auto-reconnects on speaker disconnect, finds the live stream after a stream change, and restarts after power loss.

**Key services:**
- `lofi-player.service` — the player loop (ffplay + yt-dlp)
- `lofi-web.service` — web control UI at http://10.0.0.188:8080
- `ytdlp-update.timer` — weekly yt-dlp auto-update

**Speaker:** Wuzhi Audio, Classic BT MAC `8E:EC:46:E9:7F:83`

**Jukebox:** Web UI Cover Flow for curated live discs. Play writes `lofi-override.txt` (persists across restarts). Live list cached 15m; offline catalog discs auto-fall back to Study Lofi. Details in `SETUP.md`.

**Quick commands:**
```bash
# Service control (all user services need this env prefix)
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user status|start|stop|restart lofi-player.service

# Connect speaker
bluetoothctl connect 8E:EC:46:E9:7F:83

# Check audio sinks
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus wpctl status
```

---

## 2. Morning Briefing
**Doc:** `/home/kais/MORNING-BRIEFING.md`

Cron job that sends a daily email at 8:00 AM with:
- Weather for Ypsilanti, MI
- Top 5 US news headlines
- A random Polymarket prediction market

**Recipients:** kaiusee@gmail.com + SMS via Verizon MMS gateway

**⚠️ Known issue:** Crontab points to `/home/kais/morning_briefing_cron.py` which doesn't exist.
Actual script is at `/home/kais/.hermes/skills/productivity/email-delivery/scripts/morning_briefing_cron.py`.
Crontab needs updating.

---

## 3. kais.me Daily Post Pipeline
**Doc:** `/home/kais/KAIS-POST-PIPELINE.md`

Cron job at 7:00 PM EDT that runs a 5-step AI pipeline to auto-generate a blog post for kais.me:

1. **Gemini Flash** — research + topic selection
2. **Gemini Pro** — crayon-style featured image
3. **Claude Sonnet (Thinking)** — writes the post (800-1,000 words HTML)
4. **Gemini Pro** — 18-point quality proofread + revision loop
5. **Gemini Flash** — publishes WordPress draft + emails review link

Posts are created as **drafts** and emailed to kaiusee@gmail.com for manual review before publishing.

**Manual run:**
```bash
/home/kais/scripts/post-manager/scripts/kais_post_pipeline.sh
# Resume from step 3:
/home/kais/scripts/post-manager/scripts/kais_post_pipeline.sh --from-step 3
```

---

## 4. Llamafile (Local LLM Server)
**Doc:** `/home/kais/LLAMAFILE.md`

Boot-time cron (`@reboot`, 90s delay) that starts a local LLM model server if nothing is listening on **port 8082**.

**Status:** Llamafile is **disabled** (OOM risk; `start-llamafile.sh` is a stub + `.llamafile-stopped`).
If re-enabled, it uses **8082** (8080 = lofi-web, 8081 = robot-web). Restore from `start-llamafile.sh.bak-20260609`.

---

## All Cron Jobs

```
# kais crontab
0 8 * * *    morning_briefing_cron.py        # daily email briefing (path needs fixing)
@reboot      ensure-llamafile.sh             # local LLM boot (port 8082; currently disabled)
0 19 * * *   kais_post_pipeline.sh           # kais.me daily AI blog post
```

---

## All Systemd User Services & Timers

| Unit | Purpose |
|------|---------|
| `lofi-player.service` | 24/7 lofi stream player |
| `lofi-web.service` | Web UI on port 8080 |
| `ytdlp-update.timer` | Weekly yt-dlp update |
| `atv-web.service` | Apple TV web remote on port 8083 |
| `launchpadlib-cache-clean.timer` | System cache cleanup (OS-managed) |

All user services use this env prefix:
```bash
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus systemctl --user ...
```

Lingering is enabled (`loginctl show-user kais | grep Linger` → `Linger=yes`), so services start on boot without a login session.

---

## Key File Locations

| File | Purpose |
|------|---------|
| `/home/kais/SERVER.md` | This file — master reference |
| `/home/kais/SETUP.md` | Lofi player full docs |
| `/home/kais/MORNING-BRIEFING.md` | Morning briefing cron docs |
| `/home/kais/KAIS-POST-PIPELINE.md` | kais.me post pipeline docs |
| `/home/kais/LLAMAFILE.md` | Llamafile LLM server docs |
| `/home/kais/lofi-player.sh` | Lofi player script |
| `/home/kais/lofi-web/main.py` | Web UI FastAPI backend |
| `/home/kais/lofi-web/static/index.html` | Web UI frontend |
| `/home/kais/lofi-override.txt` | Override YouTube URL (delete to resume Lofi Girl) |
| `/home/kais/lofi-stream-cache.txt` | Cached stream URL (2h TTL) |
| `/home/kais/ensure-llamafile.sh` | Llamafile boot script |
| `/home/kais/scripts/post-manager/scripts/kais_post_pipeline.sh` | Blog pipeline script |
| `~/.config/systemd/user/` | All systemd user service/timer files |
| `~/.config/wireplumber/wireplumber.conf.d/51-bluetooth-no-seat.conf` | BT headless fix |

---

## Known Issues & TODOs

1. **Morning briefing crontab path is broken** — update to point to the `.hermes` script
2. ~~**Llamafile port conflict**~~ — resolved: llamafile would use **8082**; currently disabled for OOM

## 5. KOZMO Desk Robot
**Path:** `/home/kais/robot-web`
**URL:** http://10.0.0.188:8081
**Service:** `robot-web.service` (port 8081)

Web chat brain for the TTGO T-Display face. T-Display polls `/api/display`. Auto-refreshes every 20 min with proactive PING pages.

## 6. Apple TV Web Remote
**Path:** `/home/kais/atv-web`
**URL:** http://10.0.0.188:8083
**Service:** `atv-web.service` (port 8083)

LAN web remote (pyatv Companion) for D-pad, select, menu, home, play/pause, volume.
Pair once via the UI (PIN on the TV). Credentials stored in `/home/kais/atv-web/pyatv.conf`.

```bash
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user status|restart atv-web.service
```


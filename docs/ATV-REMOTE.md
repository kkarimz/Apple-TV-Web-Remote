# Apple TV Web Remote — Dell notes

**URL:** http://10.0.0.188:8083  
**Service:** `atv-web.service`  
**Path on Dell:** `/home/kais/atv-web`

See also the master index: `/home/kais/SERVER.md` §6.

## Pairing

1. Open the URL on the same LAN  
2. Scan → choose the office Apple TV (there may be several “Office” entries)  
3. Start pairing → enter the PIN shown on the TV  
4. Credentials land in `pyatv.conf`; selected device in `settings.json`

## Service

```bash
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user status|restart atv-web.service
```

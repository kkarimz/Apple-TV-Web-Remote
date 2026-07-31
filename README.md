# Apple TV Web Remote

A fast, responsive, mobile-friendly web remote for Apple TV, hosted on your LAN. 
Designed to mimic the physical silver Siri Remote, this web app lets you control your Apple TV from any browser on your network.

<img width="500" height="762" alt="Screenshot 2026-07-31 at 3 30 26 PM" src="https://github.com/user-attachments/assets/7a801bff-0d7a-4deb-89d7-ea124ff160ec" />


Under the hood, it uses the [pyatv](https://pyatv.dev/) library's Companion protocol to communicate with your Apple TV over the network.

## Features

- **Siri Remote UI:** A beautiful, responsive interface that matches the physical silver Apple TV remote (D-pad, playback controls, volume rocker).
- **Network Pairing:** Scan for Apple TVs on your LAN and pair using the standard PIN code method.
- **Full Control:** Navigation, Select, Menu, Home, Play/Pause, Volume, and Mute.
- **Keyboard Input:** Automatically type into on-screen search fields on your TV using your phone or desktop keyboard.
- **Desktop Keyboard Support:** Use Arrow keys, Enter, Esc, and Space on your computer to navigate the TV.
- **Hold-to-Sleep:** Long-press the power button to sleep the TV, tap to wake.
- **PWA Support:** Installable as a Progressive Web App (Add to Home Screen) for a native app feel on iOS/Android.

## Requirements

- Python 3.10+
- A machine to run the server on the same LAN as your Apple TV (e.g., Raspberry Pi, home server, NAS).
- Your Apple TV must be configured to allow local network control.

## Installation (Docker)

The easiest way to run the remote is using Docker. The container needs host network access (`--network host`) so it can discover Apple TVs on your local network.

```bash
# Build the image
docker build -t atv-remote .

# Run the container (persisting settings to your current directory)
docker run -d \
  --name atv-remote \
  --network host \
  --restart unless-stopped \
  -v $(pwd)/settings.json:/app/settings.json \
  -v $(pwd)/pyatv.conf:/app/pyatv.conf \
  atv-remote
```

*Note: You may need to `touch settings.json pyatv.conf` before running the `docker run` command so Docker mounts them as files, not directories.*

---

## Installation (Manual / Systemd)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kkarimz/atv-remote.git
   cd atv-remote
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn pyatv
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8888
   ```

## Pairing your Apple TV

1. Ensure the server is running, then open the web interface on your phone or computer (`http://<server-ip>:8888`).
2. Open the **Connection** drawer at the bottom and click **Scan**.
3. Select your Apple TV from the list.
4. Your Apple TV will display a 4-digit PIN on the screen. Enter it in the web interface to pair.
5. You're connected! The credentials are automatically saved in `pyatv.conf` and `settings.json` so you won't need to pair again.

## Running as a Service (Systemd)

To keep the server running in the background, a sample systemd service file is provided in `systemd/atv-web.service`.

1. Copy the file:
   ```bash
   cp systemd/atv-web.service ~/.config/systemd/user/
   ```
2. Edit the file to match the absolute path where you cloned the repository.
3. Enable and start the service:
   ```bash
   systemctl --user enable --now atv-web.service
   ```

## Notes
- **Volume Control:** Volume buttons (`+`, `-`, `Mute`) require your Apple TV to be configured to control your TV or Receiver's volume via CEC/eARC.

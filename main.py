"""Apple TV web remote — FastAPI + pyatv on the Dell LAN."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import pyatv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pyatv import exceptions as atv_exceptions
from pyatv.const import Protocol
from pyatv.interface import AppleTV, BaseConfig, Playing
from pyatv.storage.file_storage import FileStorage

ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "settings.json"
STORAGE_FILE = ROOT / "pyatv.conf"
SCAN_TIMEOUT = 8.0
YOUTUBE_BUNDLE_ID = "com.google.ios.youtube"

# In-process session
_storage: FileStorage | None = None
_atv: AppleTV | None = None
_config: BaseConfig | None = None
_pairing: Any = None
_lock = asyncio.Lock()


def load_app_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_app_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def conf_to_dict(conf: BaseConfig) -> dict:
    protocols = []
    for s in conf.services:
        protocols.append(s.protocol.name)
    return {
        "name": conf.name,
        "address": str(conf.address) if conf.address else None,
        "identifier": conf.identifier,
        "protocols": protocols,
        "has_companion": any(s.protocol == Protocol.Companion for s in conf.services),
    }


async def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        loop = asyncio.get_running_loop()
        _storage = FileStorage(str(STORAGE_FILE), loop)
        await _storage.load()
    return _storage


async def close_atv() -> None:
    global _atv, _config
    if _atv is not None:
        try:
            _atv.close()
        except Exception:
            pass
    _atv = None
    _config = None


async def find_config(identifier: str | None = None) -> BaseConfig | None:
    loop = asyncio.get_running_loop()
    atvs = await pyatv.scan(loop, timeout=SCAN_TIMEOUT)
    if identifier:
        for conf in atvs:
            if conf.identifier == identifier:
                return conf
        return None
    settings = load_app_settings()
    wanted = settings.get("identifier")
    if wanted:
        for conf in atvs:
            if conf.identifier == wanted:
                return conf
    companion = [
        c for c in atvs
        if any(s.protocol == Protocol.Companion for s in c.services)
    ]
    office = [c for c in companion if c.name and "office" in c.name.lower()]
    if office:
        return office[0]
    return companion[0] if companion else (atvs[0] if atvs else None)


async def ensure_connected(*, force: bool = False) -> AppleTV:
    global _atv, _config
    async with _lock:
        if force and _atv is not None:
            try:
                _atv.close()
            except Exception:
                pass
            _atv = None
            _config = None
        if _atv is not None:
            return _atv
        storage = await get_storage()
        conf = await find_config()
        if conf is None:
            raise HTTPException(status_code=404, detail="No Apple TV found on the network")
        try:
            _atv = await pyatv.connect(conf, asyncio.get_running_loop(), storage=storage)
            _config = conf
            return _atv
        except Exception as e:
            _atv = None
            _config = None
            raise HTTPException(status_code=503, detail=f"Connect failed: {e}") from e


async def with_atv(coro_factory, *, retries: int = 1):
    """Run an ATV call; on failure drop session and optionally reconnect once."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            atv = await ensure_connected(force=(attempt > 0))
            return await coro_factory(atv)
        except HTTPException:
            raise
        except Exception as e:
            last_err = e
            await close_atv()
            if attempt >= retries:
                break
    raise HTTPException(status_code=503, detail=f"Remote failed: {last_err}") from last_err


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_storage()
    try:
        settings = load_app_settings()
        if settings.get("identifier") and STORAGE_FILE.exists():
            await ensure_connected()
    except Exception as e:
        print(f"[atv-web] auto-connect skipped: {e}", flush=True)
    yield
    await close_atv()
    if _pairing is not None:
        try:
            await _pairing.close()
        except Exception:
            pass


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".html", "/", ".webmanifest")) or request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.get("/api/status")
async def status():
    settings = load_app_settings()
    playing_info: dict[str, Any] | None = None
    connected = _atv is not None
    device_name = _config.name if _config else settings.get("name")
    address = str(_config.address) if _config and _config.address else settings.get("address")
    power_state = None
    keyboard: dict[str, Any] | None = None
    current_app = None

    if _atv is not None:
        try:
            playing: Playing = await _atv.metadata.playing()
            playing_info = {
                "device_state": str(playing.device_state) if playing.device_state else None,
                "title": playing.title,
                "artist": playing.artist,
                "album": playing.album,
                "app": playing.app,
                "media_type": str(playing.media_type) if playing.media_type else None,
            }
            if playing.app:
                current_app = playing.app
        except Exception:
            playing_info = None
        try:
            power_state = str(_atv.power.power_state)
        except Exception:
            power_state = None
        try:
            focus = str(_atv.keyboard.text_focus_state)
            text = None
            try:
                text = await _atv.keyboard.text_get()
            except Exception:
                text = None
            keyboard = {"focus": focus, "text": text}
        except Exception:
            keyboard = None

    return {
        "connected": connected,
        "device_name": device_name,
        "address": address,
        "identifier": settings.get("identifier") or (_config.identifier if _config else None),
        "paired": bool(settings.get("identifier")) and STORAGE_FILE.exists(),
        "playing": playing_info,
        "current_app": current_app,
        "power_state": power_state,
        "keyboard": keyboard,
    }


@app.get("/api/scan")
async def scan_devices():
    loop = asyncio.get_running_loop()
    atvs = await pyatv.scan(loop, timeout=SCAN_TIMEOUT)
    devices = [conf_to_dict(c) for c in atvs]
    devices.sort(key=lambda d: (not d["has_companion"], (d["name"] or "").lower()))
    return {"ok": True, "devices": devices, "count": len(devices)}


class PairStartPayload(BaseModel):
    identifier: str


@app.post("/api/pair/start")
async def pair_start(payload: PairStartPayload):
    global _pairing
    async with _lock:
        await close_atv()
        if _pairing is not None:
            try:
                await _pairing.close()
            except Exception:
                pass
            _pairing = None

        loop = asyncio.get_running_loop()
        atvs = await pyatv.scan(loop, timeout=SCAN_TIMEOUT)
        conf = next((c for c in atvs if c.identifier == payload.identifier), None)
        if conf is None:
            raise HTTPException(status_code=404, detail="Device not found — scan again")

        if not any(s.protocol == Protocol.Companion for s in conf.services):
            raise HTTPException(
                status_code=400,
                detail="Device has no Companion remote service (needed for D-pad)",
            )

        storage = await get_storage()
        try:
            _pairing = await pyatv.pair(
                conf, Protocol.Companion, loop, storage=storage
            )
            await _pairing.begin()
        except Exception as e:
            _pairing = None
            raise HTTPException(status_code=500, detail=f"Pairing start failed: {e}") from e

        settings = load_app_settings()
        settings.update({
            "identifier": conf.identifier,
            "name": conf.name,
            "address": str(conf.address) if conf.address else None,
            "pairing_in_progress": True,
        })
        save_app_settings(settings)

        return {
            "ok": True,
            "name": conf.name,
            "identifier": conf.identifier,
            "device_provides_pin": _pairing.device_provides_pin,
            "message": "Enter the PIN shown on your Apple TV",
        }


class PairFinishPayload(BaseModel):
    pin: str


@app.post("/api/pair/finish")
async def pair_finish(payload: PairFinishPayload):
    global _pairing, _atv, _config
    async with _lock:
        if _pairing is None:
            raise HTTPException(status_code=400, detail="No pairing in progress — start again")

        pin = payload.pin.strip().replace(" ", "")
        if not pin.isdigit():
            raise HTTPException(status_code=400, detail="PIN must be numeric")

        try:
            _pairing.pin(int(pin))
            await _pairing.finish()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Pairing failed: {e}") from e
        finally:
            try:
                await _pairing.close()
            except Exception:
                pass

        paired_ok = _pairing.has_paired
        _pairing = None

        storage = await get_storage()
        await storage.save()

        settings = load_app_settings()
        settings["pairing_in_progress"] = False
        save_app_settings(settings)

        if not paired_ok:
            raise HTTPException(status_code=400, detail="Pairing did not complete")

        conf = await find_config(settings.get("identifier"))
        if conf is None:
            return {"ok": True, "connected": False, "message": "Paired — connect when TV is reachable"}

        try:
            _atv = await pyatv.connect(conf, asyncio.get_running_loop(), storage=storage)
            _config = conf
        except Exception as e:
            return {"ok": True, "connected": False, "message": f"Paired but connect failed: {e}"}

        return {
            "ok": True,
            "connected": True,
            "name": conf.name,
            "message": f"Paired and connected to {conf.name}",
        }


@app.post("/api/connect")
async def connect_device():
    await close_atv()
    atv = await ensure_connected()
    name = _config.name if _config else "Apple TV"
    return {"ok": True, "connected": True, "name": name}


@app.post("/api/disconnect")
async def disconnect_device():
    await close_atv()
    return {"ok": True, "connected": False}


REMOTE_ACTIONS = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "select": "select",
    "menu": "menu",
    "home": "home",
    "play_pause": "play_pause",
    "volume_up": "volume_up",
    "volume_down": "volume_down",
    "top_menu": "top_menu",
    "mute": "mute",
}


@app.post("/api/remote/{action}")
async def remote_action(action: str):
    method_name = REMOTE_ACTIONS.get(action)
    if not method_name and action != "mute":
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    async def run(atv: AppleTV):
        remote = atv.remote_control
        
        if action == "mute":
            try:
                if hasattr(atv, "audio") and hasattr(atv.audio, "set_volume"):
                    await atv.audio.set_volume(0.0)
                else:
                    # Fallback if audio interface is not exposed
                    for _ in range(20):
                        await remote.volume_down()
                        await asyncio.sleep(0.05)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Mute failed: {e}")
            return {"ok": True, "action": "mute"}
            
        method = getattr(remote, method_name, None)
        if method is None:
            raise HTTPException(status_code=400, detail=f"Action not supported: {action}")
        try:
            await method()
        except atv_exceptions.BlockedStateError as e:
            raise HTTPException(status_code=409, detail=f"Blocked: {e}") from e
        return {"ok": True, "action": action}

    return await with_atv(run)


@app.post("/api/launch/{bundle_id:path}")
async def launch_app(bundle_id: str):
    async def run(atv: AppleTV):
        await atv.apps.launch_app(bundle_id)
        return {"ok": True, "bundle_id": bundle_id}

    return await with_atv(run)


class PowerPayload(BaseModel):
    action: Literal["on", "off", "wake", "sleep"]


@app.post("/api/power")
async def power_control(payload: PowerPayload):
    turn_on = payload.action in ("on", "wake")

    async def run(atv: AppleTV):
        if turn_on:
            await atv.power.turn_on()
        else:
            await atv.power.turn_off()
        state = str(atv.power.power_state)
        return {
            "ok": True,
            "action": "wake" if turn_on else "sleep",
            "power_state": state,
        }

    return await with_atv(run)


class KeyboardPayload(BaseModel):
    text: str = Field(default="", max_length=500)
    mode: Literal["set", "append"] = "set"


@app.post("/api/keyboard")
async def keyboard_input(payload: KeyboardPayload):
    text = payload.text
    if payload.mode == "append" and text == "":
        raise HTTPException(status_code=400, detail="Nothing to append")

    async def run(atv: AppleTV):
        if payload.mode == "append":
            await atv.keyboard.text_append(text)
        else:
            await atv.keyboard.text_set(text)
        current = None
        try:
            current = await atv.keyboard.text_get()
        except Exception:
            pass
        return {
            "ok": True,
            "mode": payload.mode,
            "text": current if current is not None else text,
            "focus": str(atv.keyboard.text_focus_state),
        }

    return await with_atv(run)


@app.post("/api/keyboard/clear")
async def keyboard_clear():
    async def run(atv: AppleTV):
        await atv.keyboard.text_clear()
        return {"ok": True, "text": "", "focus": str(atv.keyboard.text_focus_state)}

    return await with_atv(run)


app.mount("/", StaticFiles(directory=str(ROOT / "static"), html=True), name="static")

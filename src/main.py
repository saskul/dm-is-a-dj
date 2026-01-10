from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

from .audio import (
    play_music,
    stop_music,
    play_ambient,
    stop_ambient,
    set_music_volume,
    set_music_crossfade_time,
    set_music_loop_mode,
    set_ambient_volume,
    set_ambient_crossfade_time,
    set_ambient_loop_mode,
    play_fx
)
from .modulator import (
    list_custom_presets,
    set_custom_effect,
    load_custom_preset,
    save_custom_preset,
    delete_custom_preset
)
from .utils import get_local_ip, list_audio_files
from .state import state

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "client")
BUILD_DIR = os.path.join(FRONTEND_DIR, "build")
STATIC_DIR = os.path.join(BUILD_DIR, "static")

app = FastAPI(title="DM is a DJ 🎧")


# =======================
# STATUS
# =======================

@app.get("/status")
def status():
    return state


# =======================
# MUSIC
# =======================

@app.post("/music/play")
def music_play(track: str):
    play_music(track)
    return state["music"]


@app.post("/music/stop")
def music_stop():
    stop_music()
    return state["music"]

@app.post("/music/volume")
def music_volume(volume: float):
    set_music_volume(volume)
    return state["music"]

@app.post("/music/crossfade_time")
def music_crossfade_time(crossfade_time: float):
    set_music_crossfade_time(crossfade_time)
    return state["music"]

@app.post("/music/loop_mode")
def music_loop_mode(mode: str = None):
    set_music_loop_mode(mode)
    return state["music"]


# =======================
# AMBIENT
# =======================

@app.post("/ambient/play")
def ambient_play(track: str):
    play_ambient(track)
    return state["ambient"]


@app.post("/ambient/stop")
def ambient_stop():
    stop_ambient()
    return state["ambient"]

@app.post("/ambient/volume")
def ambient_volume(volume: float):
    set_ambient_volume(volume)
    return state["ambient"]

@app.post("/ambient/crossfade_time")
def ambient_crossfade_time(crossfade_time: float):
    set_ambient_crossfade_time(crossfade_time)
    return state["ambient"]

@app.post("/ambient/loop_mode")
def ambient_loop_mode(mode: str = None):
    set_ambient_loop_mode(mode)
    return state["ambient"]


# =======================
# VOICE FX
# =======================

@app.get("/modulator")
def voice_effects():
    return list_custom_presets()


@app.post("/modulator")
def voice_effect(effect: str):
    state["modulator"]["effect"] = load_custom_preset(effect)
    return state["modulator"]

@app.post("/modulator/custom")
def voice_effect(
    gain: float = 0.0,        # 0..10    -> wzmocnienie sygnału
    drive: float = 0.0,       # 0..1     -> przester / nasycenie
    tone: float = 0.0,        # 0..1     -> filtr niskoprzepustowy, zmienia barwę
    mix: float = 0.0,         # 0..1     -> miks dry/wet (czysty/efekt)
    pitch: float = 0.0,       # -12..12  -> pitch shift w półtonach
    chorus: float = 0.0,      # 0..1     -> głębokość efektu chorus
    delay: float = 0.0,       # 0..500   -> czas delay w ms
    reverb: float = 0.0,      # 0..1     -> ilość pogłosu
    ring_mod: float = 0.0,    # 0..2000  -> częstotliwość modulacji ring w Hz
    bitcrusher: float = 0.0   # 0..1     -> ilość redukcji bitów / cyfrowego szumu
):
    state["modulator"]["effect"] = set_custom_effect(
        gain=gain,
        drive=drive,
        tone=tone,
        mix=mix,
        pitch=pitch,
        chorus=chorus,
        delay=delay,
        reverb=reverb,
        ring_mod=ring_mod,
        bitcrusher=bitcrusher
    )
    return state["modulator"]

@app.put("/modulator")
def save_voice_effect(name: str):
    save_custom_preset(name)
    return state["modulator"]

@app.delete("/modulator")
def delete_voice_effect(name: str):
    delete_custom_preset(name)
    return state["modulator"]

# =======================
# FX
# =======================

@app.post("/fx/play")
def fx_play(track: str):
    play_fx(track)
    return state["fx"]

# =======================
# LIST TRACKS
# =======================

@app.get("/tracks/music")
def get_music_tracks():
    music_dir = os.path.join(DATA_DIR, "music")
    tracks = list_audio_files(music_dir)
    return {"tracks": tracks}


@app.get("/tracks/ambient")
def get_ambient_tracks():
    ambient_dir = os.path.join(DATA_DIR, "ambient")
    tracks = list_audio_files(ambient_dir)
    return {"tracks": tracks}


@app.get("/tracks/fx")
def get_fx_tracks():
    fx_dir = os.path.join(DATA_DIR, "fx")
    tracks = list_audio_files(fx_dir)
    return {"tracks": tracks}


# =======================
# WEBSOCKET
# =======================

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(state)
            await ws.receive_text()
    except Exception:
        pass

# =======================
# CLIENT
# =======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    print(f"✅ Mounting static files from: {STATIC_DIR}")
else:
    print(f"⚠️ Static directory not found, skipping mount: {STATIC_DIR}")

@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    """
    Fallback endpoint dla wszystkich ścieżek front-endu.
    Jeśli plik istnieje w build -> zwróć go,
    jeśli nie istnieje -> zwróć index.html (React Router handle).
    """
    requested_file = os.path.join(BUILD_DIR, full_path)

    if os.path.isfile(requested_file):
        return FileResponse(requested_file)

    # fallback do index.html
    return FileResponse(os.path.join(BUILD_DIR, "index.html"))

# =======================
# STARTUP
# =======================

@app.on_event("startup")
def announce_ip():
    local_ip = get_local_ip()
    print(f"\n🚀 The server is available at http://{local_ip}:8000 in your local network\n")

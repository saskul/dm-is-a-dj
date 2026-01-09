from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
import os

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
    set_ambient_loop_mode
)
from .fx import play_fx
from .voice_effects import set_voice_effect, available_effects
from .utils import get_local_ip, list_audio_files
from .state import state

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

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
def ambient_loop_mode(mode: float):
    set_ambient_loop_mode(mode)
    return state["ambient"]


# =======================
# VOICE FX
# =======================

@app.get("/voice/effects")
def voice_effects():
    return available_effects()


@app.post("/voice/effect/{name}")
def voice_effect(name: str):
    state["voice_effect"] = set_voice_effect(name)
    return {"voice_effect": state["voice_effect"]}


# =======================
# FX
# =======================

@app.post("/fx/play")
def fx_play(path: str):
    play_fx(path)
    return {"fx": path}

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
# STARTUP
# =======================

@app.on_event("startup")
def announce_ip():
    local_ip = get_local_ip()
    print(f"\n🚀 The server is available at http://{local_ip}:8000 in your local network\n")

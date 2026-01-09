import os
import subprocess
import json
import socket
import time
import threading
from .state import state

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MIX = os.environ.get("MIX_SINK_NAME", "mixout")

CROSSFADE_STEPS = 20
SUPPORTED_EXT = (".mp3", ".wav", ".flac", ".ogg")

# -------------------------
# Runtime-only player registry
# -------------------------
_PLAYERS = {
    "music": {"proc": None, "sock": None, "loop_stop": threading.Event()},
    "ambient": {"proc": None, "sock": None, "loop_stop": threading.Event()},
    "fx": {"proc": None, "sock": None},  # FX are fire-and-forget
}

# -------------------------
# IPC helpers
# -------------------------
def _send_mpv(sock, cmd):
    if not sock or not os.path.exists(sock):
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock)
            s.sendall(json.dumps(cmd).encode() + b"\n")
    except Exception:
        pass

def _get_prop(sock, prop):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock)
            s.sendall(json.dumps({"command": ["get_property", prop]}).encode() + b"\n")
            return json.loads(s.recv(4096).decode()).get("data")
    except Exception:
        return None

def _set_volume(sock, vol):
    vol = max(0, min(100, int(vol)))
    _send_mpv(sock, {"command": ["set_property", "volume", vol]})

def _proc_alive(proc):
    return proc and proc.poll() is None

# -------------------------
# Spawn mpv
# -------------------------
def _spawn(track, sock, loop=False, volume=100):
    cmd = [
        "mpv", track,
        "--no-video",
        f"--audio-device=pulse/{MIX}",
        f"--input-ipc-server={sock}",
        f"--volume={volume}",
    ]
    if loop:
        cmd.append("--loop")

    proc = subprocess.Popen(cmd)

    for _ in range(40):
        if os.path.exists(sock):
            return proc
        time.sleep(0.05)

    proc.terminate()
    raise RuntimeError("mpv IPC socket not created")

# -------------------------
# Crossfade
# -------------------------
def _crossfade(old_proc, old_sock, new_sock, target_vol, seconds):
    if seconds <= 0:
        if old_proc and _proc_alive(old_proc):
            old_proc.terminate()
        if new_sock:
            _set_volume(new_sock, target_vol)
        return

    step_delay = seconds / CROSSFADE_STEPS
    start_old = _get_prop(old_sock, "volume") or target_vol

    for i in range(CROSSFADE_STEPS):
        t = (i + 1) / CROSSFADE_STEPS

        if old_proc and _proc_alive(old_proc) and old_sock and os.path.exists(old_sock):
            _set_volume(old_sock, start_old * (1 - t))
        if new_sock and os.path.exists(new_sock):
            _set_volume(new_sock, target_vol * t)

        time.sleep(step_delay)

    if old_proc and _proc_alive(old_proc):
        old_proc.terminate()

# -------------------------
# Playlist helpers
# -------------------------
def _make_playlist(track_path):
    folder = os.path.dirname(track_path)
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(SUPPORTED_EXT)
    )

def _set_playlist(key):
    mode = state[key].get("loop_mode")
    track = state[key].get("track")
    if not track:
        state[key]["playlist"] = []
        state[key]["playlist_index"] = 0
        return
    full = os.path.join(DATA_DIR, key, track)
    if mode == "list":
        pl = _make_playlist(full)
        state[key]["playlist"] = pl
        state[key]["playlist_index"] = pl.index(full) if full in pl else 0
    else:
        state[key]["playlist"] = [full]
        state[key]["playlist_index"] = 0

# -------------------------
# Loop worker (shared)
# -------------------------
def _loop_worker(key):
    player = _PLAYERS[key]
    stop = player["loop_stop"]

    while not stop.is_set():
        proc, sock = player["proc"], player["sock"]
        if not proc or not sock:
            return

        pos = _get_prop(sock, "time-pos")
        dur = _get_prop(sock, "duration")

        state[key]["position"] = pos
        state[key]["duration"] = dur

        if pos is None or dur is None:
            time.sleep(0.2)
            continue

        remaining = dur - pos
        crossfade = state[key].get("crossfade_time", 0)

        if (
            state[key].get("loop_mode") == "list"
            and remaining <= crossfade
            and state[key]["playlist"]
        ):
            state[key]["playlist_index"] = (
                state[key]["playlist_index"] + 1
            ) % len(state[key]["playlist"])

            next_path = state[key]["playlist"][state[key]["playlist_index"]]
            rel = os.path.relpath(next_path, os.path.join(DATA_DIR, key))
            play(key, rel)
            return

        time.sleep(0.2)

# -------------------------
# Core player API
# -------------------------
def play(key, track):
    player = _PLAYERS[key]
    if "loop_stop" in player:
        player["loop_stop"].set()

    full = os.path.join(DATA_DIR, key, track)
    if not os.path.exists(full):
        state[key].update({"playing": False, "track": None, "position": None, "duration": None})
        return

    state[key]["track"] = track
    if key != "fx":
        _set_playlist(key)

    vol = state[key].get("volume", 100)
    fade = state[key].get("crossfade_time", 0)
    loop = state[key].get("loop_mode") == "track" if key != "fx" else False

    sock = f"/tmp/mpv_{key}_{int(time.time()*1000)}.sock"
    proc = _spawn(full, sock, loop=loop, volume=0 if key != "fx" else vol)

    if key != "fx":
        threading.Thread(target=_crossfade, args=(player["proc"], player["sock"], sock, vol, fade), daemon=True).start()

    player["proc"], player["sock"] = proc, sock
    state[key]["playing"] = True
    if key == "fx":
        state[key]["position"] = 0
        state[key]["duration"] = _get_prop(sock, "duration")

        # track FX in background and clear when finished
        def _watch_fx():
            while _proc_alive(proc):
                pos = _get_prop(sock, "time-pos")
                state[key]["position"] = pos
                time.sleep(0.05)
            state[key].update({"playing": False, "track": None, "position": None, "duration": None})
        threading.Thread(target=_watch_fx, daemon=True).start()
    elif state[key].get("loop_mode") == "list":
        player["loop_stop"].clear()
        threading.Thread(target=_loop_worker, args=(key,), daemon=True).start()

def stop(key):
    player = _PLAYERS[key]
    if "loop_stop" in player:
        player["loop_stop"].set()

    if _proc_alive(player.get("proc")):
        _crossfade(player.get("proc"), player.get("sock"), None, 0, state[key].get("crossfade_time", 0))

    player["proc"] = player["sock"] = None
    state[key].update({"playing": False, "track": None, "position": None, "duration": None})

def set_volume(key, vol):
    state[key]["volume"] = max(0, min(100, int(vol)))
    if _PLAYERS[key].get("sock"):
        _set_volume(_PLAYERS[key]["sock"], vol)

def set_loop_mode(key, mode):
    state[key]["loop_mode"] = mode
    _set_playlist(key)
    if mode == "list" and state[key]["playing"]:
        _PLAYERS[key]["loop_stop"].clear()
        threading.Thread(target=_loop_worker, args=(key,), daemon=True).start()

def set_crossfade_time(key, seconds: float):
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return
    state[key]["crossfade_time"] = max(0.0, seconds)

# -------------------------
# Public wrappers
# -------------------------
def play_music(track): play("music", track)
def stop_music(): stop("music")
def set_music_volume(v): set_volume("music", v)
def set_music_loop_mode(m): set_loop_mode("music", m)
def set_music_crossfade_time(s): set_crossfade_time("music", s)

def play_ambient(track): play("ambient", track)
def stop_ambient(): stop("ambient")
def set_ambient_volume(v): set_volume("ambient", v)
def set_ambient_loop_mode(m): set_loop_mode("ambient", m)
def set_ambient_crossfade_time(s): set_crossfade_time("ambient", s)

def play_fx(track, volume=100): 
    state.setdefault("fx", {})
    state["fx"]["volume"] = volume
    play("fx", track)

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

_music_proc = None
_music_sock = None
_ambient_proc = None
_ambient_sock = None
_music_loop_stop_event = threading.Event()
_ambient_loop_stop_event = threading.Event()


# -------------------------
# IPC helper
# -------------------------
def _send_mpv_command(sock_path, command):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock_path)
            s.sendall(json.dumps(command).encode("utf-8") + b"\n")
    except (ConnectionRefusedError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"MPV IPC error: {e}")


def _set_volume(sock_path, volume: float):
    """Clamp volume 0–100 and send to mpv"""
    if not sock_path or not os.path.exists(sock_path):
        return
    try:
        volume = max(0, min(100, int(volume)))
        cmd = {"command": ["set_property", "volume", volume]}
        _send_mpv_command(sock_path, cmd)
    except Exception as e:
        print(f"Failed to set volume: {e}")


# -------------------------
# Spawn player
# -------------------------
def _spawn_player(track_path, sock_path, loop=False, volume=100):
    cmd = [
        "mpv",
        track_path,
        "--no-video",
        f"--audio-device=pulse/{MIX}",
        f"--input-ipc-server={sock_path}",
        f"--volume={volume}",
    ]
    if loop:
        cmd.append("--loop")
    proc = subprocess.Popen(cmd)

    # Wait for IPC socket
    timeout = 2.0
    waited = 0
    while not os.path.exists(sock_path) and waited < timeout:
        time.sleep(0.05)
        waited += 0.05

    if not os.path.exists(sock_path):
        proc.terminate()
        raise RuntimeError(f"IPC socket {sock_path} did not appear")

    return proc


# -------------------------
# Crossfade
# -------------------------
def _crossfade(old_proc, old_sock, new_sock, target_volume, crossfade_time=0.0):
    if crossfade_time <= 0:
        if old_proc and old_proc.poll() is None:
            old_proc.terminate()
        if new_sock:
            _set_volume(new_sock, target_volume)
        return

    step_delay = crossfade_time / CROSSFADE_STEPS

    start_old_volume = target_volume
    if old_sock:
        v = _get_mpv_property(old_sock, "volume")
        if isinstance(v, (int, float)):
            start_old_volume = v

    for i in range(CROSSFADE_STEPS):
        t = (i + 1) / CROSSFADE_STEPS

        if old_proc and old_proc.poll() is None and old_sock:
            old_vol = int(start_old_volume * (1 - t))
            _set_volume(old_sock, old_vol)

        if new_sock:
            new_vol = int(target_volume * t)
            _set_volume(new_sock, new_vol)

        time.sleep(step_delay)

    if old_proc and old_proc.poll() is None:
        old_proc.terminate()


# -------------------------
# Playlist helper
# -------------------------
def _create_playlist_from_folder(track_path: str):
    folder = os.path.dirname(track_path)

    if not os.path.isdir(folder):
        return []


    files = sorted(
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith((".mp3", ".wav", ".flac", ".ogg"))
    )

    return [os.path.join(folder, f) for f in files]


# -------------------------
# MUSIC
# -------------------------
def set_music_playlist():
    loop_mode = state["music"].get("loop_mode")
    track_name = state["music"].get("track")
    if not track_name:
        state["music"]["playlist"] = []
        state["music"]["playlist_index"] = 0
        return

    track_path = os.path.join(DATA_DIR, "music", track_name)
    if loop_mode == "list":
        state["music"]["playlist"] = _create_playlist_from_folder(track_path)
        try:
            state["music"]["playlist_index"] = state["music"]["playlist"].index(track_path)
        except ValueError:
            state["music"]["playlist_index"] = 0
    else:
        state["music"]["playlist"] = [track_path]
        state["music"]["playlist_index"] = 0


def play_music(track: str):
    global _music_proc, _music_sock, _music_loop_stop_event
    # Stop old loop thread if running
    _music_loop_stop_event.set()

    volume = state["music"].get("volume", 100)
    crossfade_time = state["music"].get("crossfade_time", 0.0)
    loop_mode = state["music"].get("loop_mode")

    track_path = os.path.join(DATA_DIR, "music", track)

    if not os.path.exists(track_path):
        print(f"[audio] Track not found: {track_path}")
        state["music"]["playing"] = False
        state["music"]["track"] = None
        return

    state["music"]["track"] = track
    set_music_playlist()

    new_sock = f"/tmp/mpv_music_{int(time.time() * 1000)}.sock"
    loop_flag = loop_mode == "track"

    new_proc = _spawn_player(track_path, new_sock, loop=loop_flag, volume=0)

    threading.Thread(
        target=_crossfade,
        args=(_music_proc, _music_sock, new_sock, volume, crossfade_time),
        daemon=True,
    ).start()

    _music_proc = new_proc
    _music_sock = new_sock
    state["music"]["playing"] = True
    state["music"]["volume"] = volume

    # Start list loop if needed
    if loop_mode == "list":
        _music_loop_stop_event.clear()
        threading.Thread(target=_loop_list_worker, daemon=True).start()

def _get_mpv_property(sock_path, prop):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock_path)
            s.sendall(json.dumps({
                "command": ["get_property", prop]
            }).encode() + b"\n")
            data = s.recv(4096)
            return json.loads(data.decode()).get("data")
    except Exception:
        return None


def _loop_list_worker():
    while not _music_loop_stop_event.is_set():
        if not _music_proc or not _music_sock:
            return

        time_pos = _get_mpv_property(_music_sock, "time-pos")
        duration = _get_mpv_property(_music_sock, "duration")

        if time_pos is None or duration is None:
            time.sleep(0.2)
            continue

        remaining = duration - time_pos
        crossfade_time = state["music"].get("crossfade_time", 0.0)

        if remaining <= crossfade_time:
            state["music"]["playlist_index"] = (
                state["music"]["playlist_index"] + 1
            ) % len(state["music"]["playlist"])

            next_track_path = state["music"]["playlist"][state["music"]["playlist_index"]]
            rel_track = os.path.relpath(next_track_path, os.path.join(DATA_DIR, "music"))
            play_music(rel_track)
            return

        time.sleep(0.2)


def stop_music():
    global _music_proc, _music_sock

    _music_loop_stop_event.set()

    if _music_proc and _music_sock:
        crossfade_time = state["music"].get("crossfade_time", 0.0)
        _crossfade(_music_proc, _music_sock, None, 0, crossfade_time)

    _music_proc = None
    _music_sock = None
    state["music"]["playing"] = False
    state["music"]["track"] = None

    _music_loop_stop_event.clear()


def set_music_volume(volume: float):
    global _music_sock
    volume = max(0, min(100, int(volume)))
    state["music"]["volume"] = volume
    if _music_sock:
        _set_volume(_music_sock, volume)


def set_music_crossfade_time(crossfade_time: float):
    state["music"]["crossfade_time"] = crossfade_time


def set_music_loop_mode(loop_mode: str = None):
    state["music"]["loop_mode"] = loop_mode
    set_music_playlist()
    if loop_mode == "list" and state["music"]["playing"]:
        _music_loop_stop_event.clear()
        threading.Thread(target=_loop_list_worker, daemon=True).start()


# -------------------------
# AMBIENT
# -------------------------
def set_ambient_playlist():
    loop_mode = state["ambient"].get("loop_mode")
    track_name = state["ambient"].get("track")
    if not track_name:
        state["ambient"]["playlist"] = []
        state["ambient"]["playlist_index"] = 0
        return

    track_path = os.path.join(DATA_DIR, "ambient", track_name)
    if loop_mode == "list":
        state["ambient"]["playlist"] = _create_playlist_from_folder(track_path)
        try:
            state["ambient"]["playlist_index"] = state["ambient"]["playlist"].index(track_path)
        except ValueError:
            state["ambient"]["playlist_index"] = 0
    else:
        state["ambient"]["playlist"] = [track_path]
        state["ambient"]["playlist_index"] = 0


def play_ambient(track: str):
    global _ambient_proc, _ambient_sock, _ambient_loop_stop_event
    _ambient_loop_stop_event.set()

    volume = state["ambient"].get("volume", 100)
    crossfade_time = state["ambient"].get("crossfade_time", 0.0)
    loop_mode = state["ambient"].get("loop_mode")

    track_path = os.path.join(DATA_DIR, "ambient", track)
    if not os.path.exists(track_path):
        print(f"[ambient] Track not found: {track_path}")
        state["ambient"]["playing"] = False
        state["ambient"]["track"] = None
        return

    state["ambient"]["track"] = track
    set_ambient_playlist()

    loop_flag = loop_mode == "track"

    new_sock = f"/tmp/mpv_ambient_{int(time.time() * 1000)}.sock"
    new_proc = _spawn_player(track_path, new_sock, loop=loop_flag, volume=0)

    threading.Thread(
        target=_crossfade,
        args=(_ambient_proc, _ambient_sock, new_sock, volume, crossfade_time),
        daemon=True,
    ).start()

    _ambient_proc = new_proc
    _ambient_sock = new_sock
    state["ambient"]["playing"] = True
    state["ambient"]["volume"] = volume

    if loop_mode == "list":
        _ambient_loop_stop_event.clear()
        threading.Thread(target=_loop_list_worker_ambient, daemon=True).start()


def _loop_list_worker_ambient():
    global _ambient_proc, _ambient_sock

    while (
        not _ambient_loop_stop_event.is_set()
        and state["ambient"].get("loop_mode") == "list"
        and state["ambient"]["playlist"]
    ):
        if not _ambient_proc or not _ambient_sock:
            return

        time_pos = _get_mpv_property(_ambient_sock, "time-pos")
        duration = _get_mpv_property(_ambient_sock, "duration")

        if time_pos is None or duration is None:
            time.sleep(0.2)
            continue

        crossfade_time = state["ambient"].get("crossfade_time", 0.0)
        remaining = duration - time_pos

        if remaining <= crossfade_time:
            state["ambient"]["playlist_index"] = (
                state["ambient"]["playlist_index"] + 1
            ) % len(state["ambient"]["playlist"])

            next_track_path = state["ambient"]["playlist"][
                state["ambient"]["playlist_index"]
            ]
            rel_track = os.path.relpath(
                next_track_path, os.path.join(DATA_DIR, "ambient")
            )
            play_ambient(rel_track)
            return

        time.sleep(0.2)

def stop_ambient():
    global _ambient_proc, _ambient_sock

    _ambient_loop_stop_event.set()

    if _ambient_proc and _ambient_sock:
        crossfade_time = state["ambient"].get("crossfade_time", 0.0)
        _crossfade(_ambient_proc, _ambient_sock, None, 0, crossfade_time)

    _ambient_proc = None
    _ambient_sock = None
    state["ambient"]["playing"] = False
    state["ambient"]["track"] = None

    _ambient_loop_stop_event.clear()


def set_ambient_volume(volume: float):
    global _ambient_sock
    volume = max(0, min(100, int(volume)))
    state["ambient"]["volume"] = volume
    if _ambient_sock:
        _set_volume(_ambient_sock, volume)


def set_ambient_crossfade_time(crossfade_time: float):
    state["ambient"]["crossfade_time"] = crossfade_time


def set_ambient_loop_mode(loop_mode: str = None):
    state["ambient"]["loop_mode"] = loop_mode
    set_ambient_playlist()
    if loop_mode == "list" and state["ambient"]["playing"]:
        _ambient_loop_stop_event.clear()
        threading.Thread(target=_loop_list_worker_ambient, daemon=True).start()

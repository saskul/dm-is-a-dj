import os
import subprocess
from state import state

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MIX = os.environ.get("MIX_SINK_NAME", "mixout")
AMBIENT_VOLUME = os.environ.get("AMBIENT_VOLUME", "0.4")


def _spawn_player(track_path: str, loop=False, volume=None):
    """
    Launch mpv for a given track.
    """
    if not os.path.exists(track_path):
        raise FileNotFoundError(f"Track not found: {track_path}")

    cmd = ["mpv", track_path, "--no-video", f"--audio-device=pulse/{MIX}"]

    if loop:
        cmd.append("--loop")
    if volume is not None:
        cmd.append(f"--volume={int(float(volume) * 100)}")

    return subprocess.Popen(cmd)


# =======================
# MUSIC
# =======================

_music_proc = None

def play_music(track: str):
    global _music_proc
    stop_music()
    track_path = os.path.join(DATA_DIR, "music", track)
    _music_proc = _spawn_player(track_path)
    state["music"]["playing"] = True
    state["music"]["track"] = track

def stop_music():
    global _music_proc
    if _music_proc:
        _music_proc.terminate()
    _music_proc = None
    state["music"]["playing"] = False
    state["music"]["track"] = None


# =======================
# AMBIENT
# =======================

_ambient_proc = None

def play_ambient(track: str):
    global _ambient_proc
    stop_ambient()
    track_path = os.path.join(DATA_DIR, "ambient", track)
    _ambient_proc = _spawn_player(track_path, loop=True, volume=AMBIENT_VOLUME)
    state["ambient"]["playing"] = True
    state["ambient"]["track"] = track

def stop_ambient():
    global _ambient_proc
    if _ambient_proc:
        _ambient_proc.terminate()
    _ambient_proc = None
    state["ambient"]["playing"] = False
    state["ambient"]["track"] = None

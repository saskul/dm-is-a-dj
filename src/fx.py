import os
import subprocess
from state import state

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MIX = os.environ["MIX_SINK_NAME"]


def play_fx(track: str):
    track_path = os.path.join(DATA_DIR, "fx", track)
    if not os.path.exists(track_path):
        raise FileNotFoundError(f"FX track not found: {track_path}")

    subprocess.Popen([
        "aplay",
        "-D", MIX,
        track_path
    ])

    state["fx_playing"].append(track)
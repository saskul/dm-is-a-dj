import os
import threading
import sounddevice as sd
import numpy as np

# =========================
# CONFIG
# =========================
SAMPLE_RATE = 48000
BLOCK_SIZE = 128
CHANNELS = 1
MIX = os.environ.get("MIX_SINK_NAME", "mixout")

# =========================
# INTERNAL STATE
# =========================
_effect_lock = threading.Lock()
_current_effect = None
_stream = None


# =========================
# EFFECTS
# =========================
def fx_clean(x: np.ndarray) -> np.ndarray:
    return x


def fx_distortion(x: np.ndarray) -> np.ndarray:
    return np.tanh(x * 5.0) * 0.6


def fx_bitcrush(x: np.ndarray) -> np.ndarray:
    return np.round(x * 16) / 16


EFFECTS = {
    "clean": fx_clean,
    "distortion": fx_distortion,
    "bitcrush": fx_bitcrush,
}


# =========================
# AUDIO CALLBACK
# =========================
def _audio_callback(indata, outdata, frames, time, status):
    if status:
        pass

    x = indata[:, 0]

    with _effect_lock:
        fx = _current_effect

    # safeguard – stream should not run when fx is None
    if fx is None:
        outdata[:] = 0.0
        return

    outdata[:, 0] = fx(x)


# =========================
# STREAM CONTROL
# =========================
def _start_stream():
    global _stream
    if _stream is not None:
        return

    _stream = sd.Stream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype="float32",
        channels=(CHANNELS, CHANNELS),
        callback=_audio_callback,
        device=(None, MIX),
    )
    _stream.start()


def _stop_stream():
    global _stream
    if _stream is None:
        return

    _stream.stop()
    _stream.close()
    _stream = None


# =========================
# PUBLIC API (FOR CONTROLLER)
# =========================
def set_voice_effect(effect_name: str | None):
    """
    effect_name:
      - string key from EFFECTS → enable mic → MIX with effect
      - None → STOP stream, mic fully disconnected
    """
    global _current_effect

    with _effect_lock:
        if effect_name is None:
            _current_effect = None
            _stop_stream()
            return

        fx = EFFECTS.get(effect_name)
        if fx is None:
            return  # unknown effect, ignore safely

        _current_effect = fx
        _start_stream()

def available_effects():
    return EFFECTS.keys()

# =========================
# DEV TEST
# =========================
if __name__ == "__main__":
    print("🎙️ modulator ready")
    while True:
        cmd = input("effect [clean/distortion/bitcrush/none]> ").strip()
        if cmd == "none":
            set_voice_effect(None)
        else:
            set_voice_effect(cmd)
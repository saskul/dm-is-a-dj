import os
import threading
import sounddevice as sd
import numpy as np
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
PRESETS_FILE = os.path.join(DATA_DIR, "effects.json")

# =========================
# CONFIG
# =========================
SAMPLE_RATE = 48000
BLOCK_SIZE = 128
CHANNELS = 1

# =========================
# INTERNAL STATE
# =========================
_effect_lock = threading.Lock()
_current_effect = None
_stream = None
_custom_params_lock = threading.Lock()
_custom_params = None  # None = brak custom effect
_custom_last_y = 0.0   # pamięć filtra dla tone

# =========================
# EFFECTS MANAGEMENT
# =========================
def _ensure_presets_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "w") as f:
            json.dump({}, f, indent=2)

# =========================
# AUDIO CALLBACK
# =========================
def _audio_callback(indata, outdata, frames, time, status):
    if status:
        pass

    x = indata[:, 0]

    with _effect_lock:
        fx = _current_effect

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
        device=None,
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
# CUSTOM EFFECT
# =========================
def _apply_custom_effect(x: np.ndarray) -> np.ndarray:
    global _custom_last_y

    with _custom_params_lock:
        p = _custom_params.copy() if _custom_params else None

    if p is None:
        return x

    # GAIN + DRIVE
    y = x * p.get("gain", 1.0)
    y = np.tanh(y * (1 + p.get("drive", 0.0)))

    # TONE (LP filter)
    alpha = 0.1 + 0.9 * p.get("tone", 0.0)
    out = np.empty_like(y)
    last = _custom_last_y
    for i, sample in enumerate(y):
        last = alpha * sample + (1 - alpha) * last
        out[i] = last
    _custom_last_y = last

    # CHORUS
    chorus_depth = p.get("chorus", 0.0)
    if chorus_depth > 0:
        delay_samples = int(SAMPLE_RATE * 0.002)
        chorus_out = np.zeros_like(out)
        for i in range(len(out)):
            chorus_out[i] = out[i]
            if i - delay_samples >= 0:
                chorus_out[i] += chorus_depth * out[i - delay_samples]
        out = chorus_out / (1 + chorus_depth)

    # PITCH SHIFT
    pitch = p.get("pitch", 0)
    if pitch != 0:
        factor = 2 ** (pitch / 12)
        indices = np.arange(0, len(out), factor)
        indices = indices[indices < len(out)].astype(int)
        out = out[indices]
        out = np.interp(np.arange(len(y)), np.arange(len(out)), out)

    # RING MODULATION
    ring_freq = p.get("ring_mod", 0.0)
    if ring_freq > 0:
        t = np.arange(len(out)) / SAMPLE_RATE
        out = out * np.sin(2 * np.pi * ring_freq * t)

    # BITCRUSHER
    bc = p.get("bitcrusher", 0.0)
    if bc > 0:
        steps = int(1 + (1 - bc) * 256)
        out = np.round(out * steps) / steps

    # DELAY
    delay_ms = p.get("delay", 0.0)
    if delay_ms > 0:
        delay_samples = int(SAMPLE_RATE * delay_ms / 1000)
        delayed = np.zeros_like(out)
        for i in range(len(out)):
            delayed[i] = out[i]
            if i - delay_samples >= 0:
                delayed[i] += 0.5 * out[i - delay_samples]
        out = delayed / 1.5

    # REVERB
    reverb_amt = p.get("reverb", 0.0)
    if reverb_amt > 0:
        reverb_samples = [int(SAMPLE_RATE * dt) for dt in [0.03, 0.06, 0.09]]
        reverb_gain = [0.5 * reverb_amt, 0.3 * reverb_amt, 0.2 * reverb_amt]
        for d, g in zip(reverb_samples, reverb_gain):
            for i in range(d, len(out)):
                out[i] += g * out[i - d]
        out /= (1 + sum(reverb_gain))

    # MIX dry/wet
    mix = p.get("mix", 1.0)
    out = out * mix + x * (1 - mix)

    return out

# =========================
# PUBLIC API (FOR CONTROLLER)
# =========================
def save_custom_preset(name: str):
    _ensure_presets_file()
    with _custom_params_lock:
        if _custom_params is None:
            raise ValueError("The 'custom_effect' wasn't set")
        preset = _custom_params.copy()

    with open(PRESETS_FILE, "r+") as f:
        data = json.load(f)
        data[name] = preset
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def load_custom_preset(name: str):
    _ensure_presets_file()
    if name == 'off':
        _stop_stream()
        return name

    with open(PRESETS_FILE, "r") as f:
        data = json.load(f)
    preset = data.get(name)
    if preset is None:
        raise ValueError(f"Preset doesn't exist")
    set_custom_effect(
        gain=preset.get("gain", 1.0),
        drive=preset.get("drive", 0.0),
        tone=preset.get("tone", 0.0),
        mix=preset.get("mix", 1.0),
        pitch=preset.get("pitch", 0),
        chorus=preset.get("chorus", 0.0),
        delay=preset.get("delay", 0.0),
        reverb=preset.get("reverb", 0.0),
        ring_mod=preset.get("ring_mod", 0.0),
        bitcrusher=preset.get("bitcrusher", 0.0)
    )
    return name


def list_custom_presets():
    _ensure_presets_file()
    with open(PRESETS_FILE, "r") as f:
        data = json.load(f)
    return list(data.keys())


def delete_custom_preset(name: str):
    if name == "off":
        raise ValueError(f"Preset '{name}' cannot be deleted")
    _ensure_presets_file()
    with open(PRESETS_FILE, "r+") as f:
        data = json.load(f)
        if name not in data:
            raise ValueError(f"Preset '{name}' doesn't exist and cannot be deleted")
        del data[name]
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()


def set_custom_effect(gain=1.0, drive=0.0, tone=0.0, mix=1.0,
                      pitch=0, chorus=0.0, delay=0.0, reverb=0.0,
                      ring_mod=0.0, bitcrusher=0.0):
    """
    Public API: włącza niestandardowy efekt.
    gain  - wzmocnienie sygnału (0..10)
    drive - nasycenie / przester (0..1)
    tone  - barwa / filtr niskoprzepustowy (0..1)
    mix   - miks dry/wet (0..1)
    pitch - pitch shift (-12..12)
    chorus - chorus effect (0..1)
    delay - delay time in ms (0..500)
    reverb - reverb amount (0..1)
    ring_mod - ring modulation frequency in Hz (0..2000)
    bitcrusher - bitcrusher amount (0..1)
    """
    global _custom_params

    gain = max(0.0, min(10.0, float(gain)))
    drive = max(0.0, min(1.0, float(drive)))
    tone = max(0.0, min(1.0, float(tone)))
    mix = max(0.0, min(1.0, float(mix)))
    pitch = max(-12, min(12, int(pitch)))
    chorus = max(0.0, min(1.0, float(chorus)))
    delay = max(0.0, min(500.0, float(delay)))
    reverb = max(0.0, min(1.0, float(reverb)))
    ring_mod = max(0.0, min(2000.0, float(ring_mod)))
    bitcrusher = max(0.0, min(1.0, float(bitcrusher)))

    with _custom_params_lock:
        _custom_params = {
            "gain": gain,
            "drive": drive,
            "tone": tone,
            "mix": mix,
            "pitch": pitch,
            "chorus": chorus,
            "delay": delay,
            "reverb": reverb,
            "ring_mod": ring_mod,
            "bitcrusher": bitcrusher
        }

    global _current_effect
    with _effect_lock:
        _current_effect = _apply_custom_effect

    _start_stream()

    return "custom"
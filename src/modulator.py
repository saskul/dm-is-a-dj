import os
import threading
import sounddevice as sd
import numpy as np
import json
import math
from .state import state

# =========================
# CONFIG
# =========================
SAMPLE_RATE = 48000
BLOCK_SIZE = 1024  # Increased for better performance
CHANNELS = 1

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
PRESETS_FILE = os.path.join(DATA_DIR, "effects.json")

# =========================
# INTERNAL STATE
# =========================
_effect_lock = threading.Lock()
_current_effect = None
_stream = None

_custom_params_lock = threading.Lock()
_custom_params = None

# =========================
# DSP STATE (PERSISTENT)
# =========================
_low_pass_state = 0.0
_high_pass_state = 0.0
_ring_phase = 0.0
_tremolo_phase = 0.0

# Ring buffers for effects
_delay_buffer = np.zeros(SAMPLE_RATE * 2)  # 2 seconds max delay
_delay_index = 0
_delay_feedback_buffer = np.zeros(SAMPLE_RATE * 2)

_chorus_buffers = [np.zeros(int(SAMPLE_RATE * 0.03)) for _ in range(3)]
_chorus_indices = [0, 0, 0]
_chorus_phases = [0.0, 0.0, 0.0]

_reverb_buffer = np.zeros(int(SAMPLE_RATE * 1.5))  # 1.5 second reverb buffer
_reverb_index = 0

# =========================
# VOLUME STATE
# =========================
_volume_lock = threading.Lock()
_volume = 1.0

# Load initial volume from state
try:
    initial_volume = float(getattr(state.modulator, "volume", 100))
except Exception:
    initial_volume = 100.0

with _volume_lock:
    _volume = max(0.0, min(1.0, initial_volume / 100.0))

# =========================
# PRESET FILE
# =========================
def _ensure_presets_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PRESETS_FILE):
        default_presets = {
            "off": None,
            "demon": {
                "gain": 7.5,
                "drive": 0.9,
                "tone": 0.3,
                "mix": 1.0,
                "pitch": -12,
                "chorus": 0.4,
                "delay": 45,
                "reverb": 0.4,
                "ring_mod": 60,
                "bitcrusher": 0.05,
                "low_pass": 1800
            },
            "ghost": {
                "gain": 6.0,
                "drive": 0.15,
                "tone": 0.85,
                "mix": 1.0,
                "pitch": 6,
                "chorus": 0.7,
                "delay": 200,
                "reverb": 0.8,
                "ring_mod": 0.2,
                "bitcrusher": 0.02,
                "high_pass": 800,
                "tremolo": 5
            }
        }
        with open(PRESETS_FILE, "w") as f:
            json.dump(default_presets, f, indent=2)

# =========================
# AUDIO CALLBACK
# =========================
def _audio_callback(indata, outdata, frames, time, status):
    if status:
        print(f"Audio status: {status}")
    
    x = indata[:, 0].copy()
    
    with _effect_lock:
        fx_func = _current_effect
    
    with _volume_lock:
        vol = _volume

    if fx_func is None:
        # Off mode safe assignment
        outdata[:, 0] = np.clip(x * vol, -1.0, 1.0)
    else:
        y = fx_func(x)
        outdata[:, 0] = np.clip(y * vol, -1.0, 1.0)



# =========================
# STREAM CONTROL
# =========================
def _start_stream():
    global _stream
    if _stream:
        return
    
    _stream = sd.Stream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype="float32",
        channels=(CHANNELS, CHANNELS),
        callback=_audio_callback,
    )
    _stream.start()

def _stop_stream():
    global _stream
    if not _stream:
        return
    _stream.stop()
    _stream.close()
    _stream = None

# =========================
# FILTER FUNCTIONS
# =========================
def _pitch_shift(x: np.ndarray, semitones: float) -> np.ndarray:
    """Real-time safe pitch shift for any semitone -36 to +24"""
    if semitones == 0:
        return x
    factor = 2 ** (semitones / 12.0)
    factor = max(factor, 0.0625)  # Limit -36 semitones
    old_len = len(x)
    new_len = int(old_len / factor)
    new_indices = np.linspace(0, old_len - 1, new_len)
    y = np.interp(new_indices, np.arange(old_len), x)
    if len(y) > old_len:
        y = y[:old_len]
    else:
        y = np.pad(y, (0, old_len - len(y)), 'constant')
    return y

def _apply_low_pass(signal, cutoff_hz):
    """Apply one-pole low-pass filter"""
    global _low_pass_state
    if cutoff_hz <= 0:
        return signal
    
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    alpha = dt / (rc + dt)
    
    result = np.zeros_like(signal)
    last = _low_pass_state
    
    for i in range(len(signal)):
        last = last + alpha * (signal[i] - last)
        result[i] = last
    
    _low_pass_state = last
    return result

def _apply_high_pass(signal, cutoff_hz):
    """Apply one-pole high-pass filter"""
    global _high_pass_state
    if cutoff_hz <= 0:
        return signal
    
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    alpha = rc / (rc + dt)
    
    result = np.zeros_like(signal)
    last = _high_pass_state
    
    for i in range(len(signal)):
        highpass = alpha * (last + signal[i] - (signal[i-1] if i > 0 else 0))
        result[i] = highpass
        last = highpass
    
    _high_pass_state = last
    return result

# =========================
# EFFECT PROCESSOR
# =========================
def _apply_custom_effect(x: np.ndarray) -> np.ndarray:
    global _ring_phase, _tremolo_phase, _delay_index, _reverb_index, _chorus_indices, _chorus_phases

    with _custom_params_lock:
        p = _custom_params.copy() if _custom_params else {}
    
    if not p:
        return x

    y = x.copy()

    # GAIN
    y *= 10 ** (p.get("gain", 0) / 20.0)

    # DISTORTION
    drive = p.get("drive", 0.0)
    if drive > 0:
        y = np.tanh(y * (1.0 + drive * 3.0))

    # PITCH SHIFT
    y = _pitch_shift(y, p.get("pitch", 0))

    # TONE
    tone = p.get("tone", 0.5)
    if tone < 0.5:
        cutoff = 1000 + 15000 * (tone * 2)
        y = _apply_low_pass(y, cutoff)

    # FILTERS
    if p.get("low_pass", 0) > 0:
        y = _apply_low_pass(y, p["low_pass"])
    if p.get("high_pass", 0) > 0:
        y = _apply_high_pass(y, p["high_pass"])

    # CHORUS
    chorus = p.get("chorus", 0)
    if chorus > 0:
        chorus_mixed = y.copy()
        for i in range(3):
            delay_samples = int(SAMPLE_RATE * (0.005 + i * 0.003))
            rate = 0.5 + i * 0.3
            depth = 0.001 + i * 0.0005
            _chorus_phases[i] += 2 * math.pi * rate / SAMPLE_RATE
            _chorus_phases[i] %= 2 * math.pi
            mod_depth = int(depth * SAMPLE_RATE * (1 + math.sin(_chorus_phases[i])))
            actual_delay = delay_samples + mod_depth
            buf = _chorus_buffers[i]
            idx = _chorus_indices[i]
            buf_len = len(buf)
            delayed = np.zeros_like(y)
            for j in range(len(y)):
                read_idx = (idx - actual_delay) % buf_len
                delayed[j] = buf[int(read_idx)]
                buf[idx] = y[j]
                idx = (idx + 1) % buf_len
            _chorus_indices[i] = idx
            chorus_mixed += delayed * chorus * 0.3
        y = chorus_mixed / (1 + 3 * chorus * 0.3)

    # RING MOD
    ring_freq = p.get("ring_mod", 0)
    if ring_freq > 0:
        t = np.arange(len(y)) / SAMPLE_RATE
        y *= 1 + 0.7 * np.sin(2 * math.pi * ring_freq * t + _ring_phase)
        _ring_phase += 2 * math.pi * ring_freq * len(y) / SAMPLE_RATE
        _ring_phase %= 2 * math.pi

    # BITCRUSHER
    bitcrush = p.get("bitcrusher", 0)
    if bitcrush > 0:
        bits = 16 - int(bitcrush * 12)
        levels = 2 ** bits
        y = np.round(y * levels) / levels

    # DELAY
    delay_ms = p.get("delay", 0)
    if delay_ms > 0:
        delay_samples = int(SAMPLE_RATE * delay_ms / 1000)
        wet = np.zeros_like(y)
        buf = _delay_buffer
        fb_buf = _delay_feedback_buffer
        idx = _delay_index
        for i in range(len(y)):
            read_idx = (idx - delay_samples) % len(buf)
            delayed = buf[read_idx] * 0.6 + fb_buf[read_idx] * 0.3
            wet[i] = delayed
            buf[idx] = y[i]
            fb_buf[idx] = delayed * 0.5
            idx = (idx + 1) % len(buf)
        _delay_index = idx
        y += wet * 0.7

    # REVERB
    reverb = p.get("reverb", 0)
    if reverb > 0:
        delays = [int(SAMPLE_RATE * t) for t in [0.0297, 0.0371, 0.0411, 0.0437]]
        gains = [0.8, 0.6, 0.5, 0.4]
        buf = _reverb_buffer
        idx = _reverb_index
        for i in range(len(y)):
            reverb_sum = sum(buf[(idx - d) % len(buf)] * g * reverb for d, g in zip(delays, gains))
            buf[idx] = y[i] + reverb_sum * 0.7
            y[i] = y[i] * (1 - reverb * 0.3) + reverb_sum * reverb
            idx = (idx + 1) % len(buf)
        _reverb_index = idx

    # TREMOLO
    tremolo_hz = p.get("tremolo", 0)
    if tremolo_hz > 0:
        t = np.arange(len(y)) / SAMPLE_RATE
        y *= 1.0 - 0.5 * (1 + np.sin(2 * math.pi * tremolo_hz * t + _tremolo_phase))
        _tremolo_phase += 2 * math.pi * tremolo_hz * len(y) / SAMPLE_RATE
        _tremolo_phase %= 2 * math.pi


    # DRY/WET mix
    mix = p.get("mix", 1.0)
    if mix < 1.0:
        y = y * mix + x * (1 - mix)

    return np.clip(y, -1.0, 1.0)

# =========================
# PUBLIC API
# =========================
def set_custom_effect(**params):
    """Set custom effect parameters"""
    global _custom_params, _current_effect
    
    # Reset DSP states when changing effects
    global _low_pass_state, _high_pass_state, _ring_phase, _tremolo_phase
    global _delay_index, _reverb_index, _chorus_indices, _chorus_phases
    
    _low_pass_state = 0.0
    _high_pass_state = 0.0
    _ring_phase = 0.0
    _tremolo_phase = 0.0
    _delay_index = 0
    _reverb_index = 0
    _chorus_indices = [0, 0, 0]
    _chorus_phases = [0.0, 0.0, 0.0]
    
    # Clear buffers
    _delay_buffer.fill(0)
    _delay_feedback_buffer.fill(0)
    _reverb_buffer.fill(0)
    for buf in _chorus_buffers:
        buf.fill(0)
    
    with _custom_params_lock:
        _custom_params = {
            "gain": float(params.get("gain", 0)),
            "drive": float(params.get("drive", 0)),
            "tone": float(params.get("tone", 0.5)),
            "mix": float(params.get("mix", 1)),
            "pitch": int(params.get("pitch", 0)),
            "chorus": float(params.get("chorus", 0)),
            "delay": float(params.get("delay", 0)),
            "reverb": float(params.get("reverb", 0)),
            "ring_mod": float(params.get("ring_mod", 0)),
            "bitcrusher": float(params.get("bitcrusher", 0)),
            "low_pass": float(params.get("low_pass", 0)),
            "high_pass": float(params.get("high_pass", 0)),
            "tremolo": float(params.get("tremolo", 0)),
        }
    
    with _effect_lock:
        _current_effect = _apply_custom_effect
    
    _start_stream()
    return "custom"

def save_custom_preset(name):
    """Save current effect settings as a named preset"""
    _ensure_presets_file()
    
    with _custom_params_lock:
        if _custom_params is None:
            raise ValueError("No effect parameters to save")
        preset = _custom_params.copy()
    
    with open(PRESETS_FILE, "r+") as f:
        data = json.load(f)
        data[name] = preset
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    return f"Preset '{name}' saved"

def load_custom_preset(name):
    """Load a named preset"""
    _ensure_presets_file()
    
    if name == 'off':
        set_effect_off()
        return 'off'
    
    with open(PRESETS_FILE, 'r') as f:
        data = json.load(f)
    
    if name not in data:
        raise ValueError(f"Preset '{name}' not found")
    
    preset = data[name]
    if preset is None:  # "off" preset
        set_effect_off()
    else:
        set_custom_effect(**preset)
    
    return name

def list_custom_presets():
    """List all available presets"""
    _ensure_presets_file()
    
    with open(PRESETS_FILE, 'r') as f:
        data = json.load(f)
    
    return data

def delete_custom_preset(name):
    """Delete a named preset"""
    _ensure_presets_file()
    
    with open(PRESETS_FILE, "r+") as f:
        data = json.load(f)
        
        if name not in data:
            raise ValueError(f"Preset '{name}' not found")
        
        if name == "off" or name == "demon" or name == "ghost":
            raise ValueError(f"Cannot delete built-in preset '{name}'")
        
        del data[name]
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
    
    return f"Preset '{name}' deleted"

def set_effect_off():
    """Turn off all effects"""
    global _current_effect
    
    with _effect_lock:
        _current_effect = None
    
    # Don't stop stream, just pass through
    _start_stream()
    return "off"

def set_demon_effect():
    """Set demon effect preset"""
    return load_custom_preset("demon")

def set_ghost_effect():
    """Set ghost effect preset"""
    return load_custom_preset("ghost")

def get_current_preset():
    """Get name of current preset"""
    _ensure_presets_file()
    
    with open(PRESETS_FILE, 'r') as f:
        data = json.load(f)
    
    with _custom_params_lock:
        if _custom_params is None:
            return "off"
        
        for name, preset in data.items():
            if preset is None:
                continue
            if all(abs(_custom_params.get(k, 0) - preset.get(k, 0)) < 0.01 
                   for k in preset.keys()):
                return name
    
    return "custom"

def set_modulator_volume(value):
    """Set master volume (0-100)"""
    global _volume
    
    with _volume_lock:
        _volume = max(0.0, min(1.0, float(value) / 100.0))
    
    # Save to state if available
    if hasattr(state, 'modulator'):
        state.modulator.volume = int(value)
    
    return f"Volume set to {value}%"

def get_current_volume():
    """Get current volume percentage"""
    with _volume_lock:
        return int(_volume * 100)
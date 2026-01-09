import os
import subprocess

VOICE_EFFECTS = {
    "off": None,

    "microshift": {
        "plugin": "microshift",
        "label": "MicroShift",
    },

    "robot": {
        "plugin": "ringmod",
        "label": "Ring Modulator",
    },

    "pitch_up": {
        "plugin": "pitch",
        "label": "Pitch Shifter",
    },

    "demon": {
        "plugin": "pitch",
        "label": "Pitch Shifter",
    },
}


def _run(cmd: list[str]):
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _get_loaded_ladspa_module_id() -> str | None:
    out = subprocess.check_output(["pactl", "list", "short", "modules"]).decode()
    for line in out.splitlines():
        if "module-ladspa-sink" in line:
            return line.split("\t")[0]
    return None


def disable_voice_effect():
    mod_id = _get_loaded_ladspa_module_id()
    if mod_id:
        _run(["pactl", "unload-module", mod_id])


def enable_voice_effect(effect: dict):
    disable_voice_effect()

    _run([
        "pactl", "load-module", "module-ladspa-sink",
        f"sink_name={os.environ['VOICE_EFFECT_SINK']}",
        f"plugin={effect['plugin']}",
        f"label={effect['label']}",
    ])


def set_voice_effect(name: str):
    effect = VOICE_EFFECTS.get(name)
    if effect is None:
        disable_voice_effect()
        return "off"

    enable_voice_effect(effect)
    return name


def available_effects():
    return list(VOICE_EFFECTS.keys())

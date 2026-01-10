import os
import subprocess
import time
import json
import signal
import threading
import select
import fcntl
import errno
from .state import state

# Configuration
MIX = os.environ.get("MIX_SINK_NAME", "mixout")
VOICE_EFFECTS = {
    "off": {
        "label": "Off",
        "effect": None
    },
    "microshift": {
        "label": "MicroShift",
        "effect": "chorus 0.7 0.9 55 0.4 0.25 2 -t",
        "description": "Creates a micro pitch shift effect"
    },
    "robot": {
        "label": "Robot",
        "effect": "overdrive 20",
        "description": "Robot voice effect"
    },
    "pitch_up": {
        "label": "Pitch Up",
        "effect": "pitch 300",
        "description": "Higher pitch (1.5x)"
    },
    "demon": {
        "label": "Demon",
        "effect": "pitch -500",
        "description": "Lower pitch (0.7x)"
    },
    "echo": {
        "label": "Echo",
        "effect": "echo 0.8 0.5 100 0.5",
        "description": "Echo effect"
    },
    "reverb": {
        "label": "Reverb",
        "effect": "reverb 50 50 100 100 0 0",
        "description": "Reverb effect"
    },
    "radio": {
        "label": "Radio",
        "effect": "overdrive 10 band 1000 2000",
        "description": "AM radio effect"
    },
    "slow": {
        "label": "Slow Motion",
        "effect": "stretch 1.5",
        "description": "Slow down audio"
    },
    "fast": {
        "label": "Fast Motion",
        "effect": "stretch 0.7",
        "description": "Speed up audio"
    },
    "telephone": {
        "label": "Telephone",
        "effect": "bandpass 300 3000",
        "description": "Telephone filter"
    },
    "flanger": {
        "label": "Flanger",
        "effect": "flanger 0 2 0 71 0.5 25 linear",
        "description": "Flanger effect"
    },
    "phaser": {
        "label": "Phaser",
        "effect": "phaser 0.8 0.74 3 0.7 0.5",
        "description": "Phaser effect"
    },
    "tremolo": {
        "label": "Tremolo",
        "effect": "tremolo 5 50",
        "description": "Tremolo effect"
    }
}

# Default configuration - REDUCED LATENCY SETTINGS
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "voice_config.json")
DEFAULT_CONFIG = {
    "input_source": "default",
    "volume": 1.0,
    "latency_ms": 5,  # Reduced from 20ms
    "sample_rate": 44100,
    "channels": 2,
    "buffer_size": 256  # Reduced from 1024
}

class VoiceModulator:
    def __init__(self):
        """Initialize voice modulator with low-latency approach"""
        self.sox_process = None
        self.current_effect = "off"
        self.config = self._load_config()
        self._stop_event = threading.Event()
        self._process_thread = None
        self._lock = threading.Lock()
        self._audio_buffer = bytearray()
        
    def _load_config(self):
        """Load configuration from file"""
        config = DEFAULT_CONFIG.copy()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    config.update(loaded)
        except Exception as e:
            print(f"Could not load voice config: {e}")
        return config
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Could not save voice config: {e}")
    
    def _run_command(self, cmd, capture=False, shell=False):
        """Run a command and optionally capture output"""
        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    shell=shell,
                    capture_output=True,
                    text=True,
                    check=False
                )
                return result
            else:
                subprocess.run(
                    cmd,
                    shell=shell,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                return None
        except FileNotFoundError:
            print(f"Command not found: {cmd}")
            return None
    
    def _get_pulseaudio_input(self):
        """Get the PulseAudio input source"""
        source = self.config.get("input_source", "default").strip()
        if source == "default":
            # Get default source
            result = self._run_command(["pactl", "get-default-source"], capture=True)
            if result and result.returncode == 0:
                source = result.stdout.strip()
            else:
                # List available sources and pick the first non-monitor
                result = self._run_command(["pactl", "list", "short", "sources"], capture=True)
                if result and result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line and ".monitor" not in line:
                            source = line.split('\t')[1]
                            break
        
        return source
    
    def _ensure_mix_sink_exists(self):
        """Ensure the MIX sink exists"""
        result = self._run_command(["pactl", "list", "short", "sinks"], capture=True)
        if result and result.returncode == 0:
            sinks = result.stdout.strip().split('\n')
            for sink in sinks:
                if sink and MIX in sink.split('\t')[1]:
                    return True
        
        # Create the MIX sink if it doesn't exist
        print(f"Creating MIX sink: {MIX}")
        self._run_command([
            "pactl", "load-module", "module-null-sink",
            f"sink_name={MIX}",
            "sink_properties=device.description='Mix_Sink'",
            "rate=44100",  # Explicitly set sample rate
            "channels=2"
        ])
        
        # Verify creation
        time.sleep(0.1)  # Reduced sleep
        result = self._run_command(["pactl", "list", "short", "sinks"], capture=True)
        if result and result.returncode == 0:
            for sink in result.stdout.strip().split('\n'):
                if sink and MIX in sink.split('\t')[1]:
                    return True
        
        return False
    
    def _build_pipeline_command(self, effect_config):
        """Build a LOW LATENCY shell pipeline command"""
        # Get input source
        input_source = self._get_pulseaudio_input()
        
        # Get audio format parameters
        rate = str(self.config.get("sample_rate", 44100))
        channels = str(self.config.get("channels", 2))
        latency_ms = self.config.get("latency_ms", 5)
        latency_bytes = str(int(latency_ms * rate * 2 * int(channels) / 1000))
        
        # Build volume adjustment
        volume = self.config.get("volume", 1.0)
        volume_cmd = f"vol {volume}" if volume != 1.0 else ""
        
        # Build effect command
        effect_cmd = effect_config.get("effect", "") if effect_config else ""
        
        # Combine all Sox effects
        sox_effects = " ".join(filter(None, [volume_cmd, effect_cmd]))
        
        # Use LOW LATENCY parameters for parec/pacat
        if sox_effects.strip():
            cmd = (
                f"parec --device={input_source} "
                f"--format=s16le --rate={rate} --channels={channels} "
                f"--latency={latency_bytes} --process-time={latency_ms} | "
                f"sox -q -t raw -r {rate} -e signed-integer -b 16 -c {channels} - "
                f"-t raw - {sox_effects} "
                f"--buffer {self.config.get('buffer_size', 256)} "
                f"--no-show-progress | "
                f"pacat --device={MIX} --format=s16le --rate={rate} --channels={channels} "
                f"--latency={latency_bytes} --stream-name=VoiceMod"
            )
        else:
            # Direct passthrough without effects (for 'off' mode)
            cmd = (
                f"parec --device={input_source} "
                f"--format=s16le --rate={rate} --channels={channels} "
                f"--latency={latency_bytes} --process-time={latency_ms} | "
                f"pacat --device={MIX} --format=s16le --rate={rate} --channels={channels} "
                f"--latency={latency_bytes} --stream-name=VoiceMod"
            )
        
        return cmd
    
    def _stop_pipeline_process(self):
        """Stop the running pipeline process"""
        with self._lock:
            if self.sox_process and self.sox_process.poll() is None:
                try:
                    # Get the process group ID
                    pgid = os.getpgid(self.sox_process.pid)
                    
                    # First, try graceful termination
                    os.killpg(pgid, signal.SIGTERM)
                    
                    # Wait briefly
                    time.sleep(0.1)
                    
                    if self.sox_process.poll() is None:
                        # Force kill if still running
                        os.killpg(pgid, signal.SIGKILL)
                        self.sox_process.wait(timeout=0.5)
                        
                except Exception as e:
                    print(f"Error stopping pipeline process: {e}")
                    try:
                        # Fallback
                        self.sox_process.terminate()
                        self.sox_process.wait(timeout=0.1)
                    except:
                        try:
                            self.sox_process.kill()
                            self.sox_process.wait()
                        except:
                            pass
                finally:
                    self.sox_process = None
    
    def _start_pipeline_process(self, effect_config):
        """Start pipeline process with the given effect"""
        # Stop any existing process
        self._stop_pipeline_process()
        
        # Ensure MIX sink exists
        if not self._ensure_mix_sink_exists():
            print(f"Failed to create or find MIX sink: {MIX}")
            return False
        
        # Build command
        cmd = self._build_pipeline_command(effect_config)
        
        print(f"Starting LOW-LATENCY pipeline...")
        
        try:
            # Start the pipeline with reduced buffer
            self.sox_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
                bufsize=0  # No buffering
            )
            
            # Reduced wait time
            time.sleep(0.2)
            
            if self.sox_process.poll() is not None:
                print("Pipeline failed to start")
                self.sox_process = None
                return False
            
            print(f"Pipeline started (PID: {self.sox_process.pid})")
            return True
            
        except FileNotFoundError as e:
            print(f"Required command not found: {e}")
            print("Please install: sudo apt-get install pulseaudio-utils sox")
            return False
        except Exception as e:
            print(f"Failed to start pipeline: {e}")
            return False
    
    def _change_effect_without_restart(self, effect_config):
        """Experimental: Try to change effect without full restart"""
        # This is a placeholder for a more advanced approach
        # where we could use a FIFO or named pipe to feed sox
        # For now, we'll stick with restart but faster
        
        # Clear any audio buffer
        self._audio_buffer = bytearray()
        
        # Restart with new effect
        return self._start_pipeline_process(effect_config)
    
    def _cleanup(self):
        """Clean up pipeline process"""
        self._stop_pipeline_process()
    
    def set_effect(self, effect_name):
        """Set the voice effect with minimal delay"""
        if effect_name == self.current_effect:
            return effect_name
        
        effect_config = VOICE_EFFECTS.get(effect_name)
        
        if effect_name == "off" or not effect_config:
            self._cleanup()
            self.current_effect = "off"
            state["voice_effect"] = "off"
            print("Voice effect disabled")
            return "off"
        
        # Use faster effect switching
        if self._change_effect_without_restart(effect_config):
            self.current_effect = effect_name
            state["voice_effect"] = effect_config.get("label", effect_name)
            print(f"Voice effect '{effect_config['label']}' activated")
            return effect_name
        else:
            # Fallback to standard method
            if self._start_pipeline_process(effect_config):
                self.current_effect = effect_name
                state["voice_effect"] = effect_config.get("label", effect_name)
                print(f"Voice effect '{effect_config['label']}' activated")
                return effect_name
            else:
                self.current_effect = "off"
                state["voice_effect"] = "off"
                print(f"Failed to set effect: {effect_name}")
                return "off"
    
    def set_volume(self, volume):
        """Set voice effect volume (0.0 to 2.0)"""
        volume = max(0.0, min(2.0, volume))
        old_volume = self.config.get("volume", 1.0)
        self.config["volume"] = volume
        self._save_config()
        
        # Restart effect if volume changed and effect is active
        if self.current_effect != "off" and abs(old_volume - volume) > 0.01:
            effect_config = VOICE_EFFECTS.get(self.current_effect)
            if effect_config:
                self._start_pipeline_process(effect_config)
    
    def set_input_source(self, source_name):
        """Set the microphone source"""
        old_source = self.config.get("input_source", "default")
        self.config["input_source"] = source_name
        self._save_config()
        
        # Restart effect if source changed and effect is active
        if self.current_effect != "off" and old_source != source_name:
            effect_config = VOICE_EFFECTS.get(self.current_effect)
            if effect_config:
                self._start_pipeline_process(effect_config)
    
    def list_input_sources(self):
        """List available microphone sources"""
        sources = []
        result = self._run_command(["pactl", "list", "short", "sources"], capture=True)
        if result and result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        source_info = {
                            "id": parts[0],
                            "name": parts[1],
                            "description": parts[1]
                        }
                        if len(parts) > 2:
                            source_info["description"] = parts[2]
                        # Filter out monitors (outputs)
                        if ".monitor" not in source_info["name"]:
                            sources.append(source_info)
        return sources
    
    def list_sinks(self):
        """List available sinks"""
        sinks = []
        result = self._run_command(["pactl", "list", "short", "sinks"], capture=True)
        if result and result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        sink_info = {
                            "id": parts[0],
                            "name": parts[1],
                            "description": parts[1]
                        }
                        if len(parts) > 2:
                            sink_info["description"] = parts[2]
                        sinks.append(sink_info)
        return sinks
    
    def get_status(self):
        """Get current status"""
        return {
            "effect": self.current_effect,
            "effect_label": VOICE_EFFECTS.get(self.current_effect, {}).get("label", "Off"),
            "volume": self.config.get("volume", 1.0),
            "input_source": self.config.get("input_source", "default"),
            "mix_sink": MIX,
            "process_running": self.sox_process is not None and self.sox_process.poll() is None
        }
    
    def test_microphone(self, duration=3):
        """Test microphone by routing it directly to MIX sink"""
        print(f"Testing microphone for {duration} seconds...")
        
        # Ensure MIX sink exists
        if not self._ensure_mix_sink_exists():
            print(f"Failed to create or find MIX sink: {MIX}")
            return False
        
        # Get microphone source
        sources = self.list_input_sources()
        if not sources:
            print("No microphone sources found!")
            return False
        
        mic_source = sources[0]["name"]
        
        # Build LOW LATENCY test command
        latency_ms = 5
        rate = 44100
        channels = 2
        latency_bytes = str(int(latency_ms * rate * 2 * channels / 1000))
        
        cmd = (
            f"parec --device={mic_source} "
            f"--format=s16le --rate={rate} --channels={channels} "
            f"--latency={latency_bytes} --process-time={latency_ms} | "
            f"pacat --device={MIX} --format=s16le --rate={rate} --channels={channels} "
            f"--latency={latency_bytes}"
        )
        
        try:
            print(f"Starting microphone test...")
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
                bufsize=0
            )
            
            print(f"You should hear yourself for {duration} seconds...")
            time.sleep(duration)
            
            # Kill the process group
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(0.1)
                if process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
                    process.wait()
            except:
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
                    
            print("Microphone test complete")
            return True
            
        except Exception as e:
            print(f"Microphone test failed: {e}")
            return False

# Alternative: Using PulseAudio modules directly (even lower latency)
class PulseAudioVoiceModulator:
    """Alternative implementation using PulseAudio modules directly"""
    
    def __init__(self):
        self.current_effect = "off"
        self.config = self._load_config()
        self.module_id = None
        
    def _load_config(self):
        """Load configuration from file"""
        config = DEFAULT_CONFIG.copy()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    config.update(loaded)
        except Exception as e:
            print(f"Could not load voice config: {e}")
        return config
    
    def set_effect(self, effect_name):
        """Set effect using PulseAudio module-echo-cancel for lower latency"""
        if effect_name == self.current_effect:
            return effect_name
        
        effect_config = VOICE_EFFECTS.get(effect_name)
        
        # Unload existing module
        if self.module_id:
            subprocess.run(["pactl", "unload-module", str(self.module_id)], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.module_id = None
        
        if effect_name == "off" or not effect_config:
            self.current_effect = "off"
            state["voice_effect"] = "off"
            print("Voice effect disabled")
            return "off"
        
        # For certain effects, we can use PulseAudio's built-in modules
        # This is much faster than shell pipelines
        if effect_name == "echo":
            # Use module-echo-cancel with custom parameters
            cmd = [
                "pactl", "load-module", "module-echo-cancel",
                "use_master_format=1",
                "aec_method=webrtc",
                f"source_name=voice_effect_{effect_name}",
                f"sink_name=voice_effect_{effect_name}_sink"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip().isdigit():
                self.module_id = int(result.stdout.strip())
                self.current_effect = effect_name
                state["voice_effect"] = effect_config.get("label", effect_name)
                print(f"Voice effect '{effect_config['label']}' activated via PulseAudio")
                return effect_name
        
        # Fallback to standard method
        _voice_modulator.set_effect(effect_name)
        return effect_name

# Create global instance
_voice_modulator = VoiceModulator()
# Optional: Use PulseAudio version for certain effects
# _voice_modulator = PulseAudioVoiceModulator()

# Public API functions
def disable_voice_effect():
    """Disable voice effect"""
    _voice_modulator.set_effect("off")

def enable_voice_effect(effect: dict):
    """Enable voice effect - takes effect dict from VOICE_EFFECTS"""
    if not effect:
        disable_voice_effect()
        return
    
    effect_name = "off"
    for name, config in VOICE_EFFECTS.items():
        if config == effect:
            effect_name = name
            break
    
    _voice_modulator.set_effect(effect_name)

def set_voice_effect(name: str):
    """Set voice effect by name"""
    return _voice_modulator.set_effect(name)

def available_effects():
    """Get list of available effect names"""
    return list(VOICE_EFFECTS.keys())

def set_voice_volume(volume: float):
    """Set voice effect volume (0.0 to 2.0)"""
    _voice_modulator.set_volume(volume)

def set_voice_input_source(source_name: str):
    """Set microphone input source"""
    _voice_modulator.set_input_source(source_name)

def list_voice_input_sources():
    """List available microphone sources"""
    return _voice_modulator.list_input_sources()

def list_audio_sinks():
    """List available audio sinks"""
    return _voice_modulator.list_sinks()

def get_voice_status():
    """Get current voice modulation status"""
    return _voice_modulator.get_status()

def test_microphone(duration=3):
    """Test microphone routing"""
    return _voice_modulator.test_microphone(duration)

def cleanup():
    """Clean up all voice modulation modules"""
    _voice_modulator._cleanup()

def reload_config():
    """Reload configuration from file"""
    _voice_modulator.reload_config()
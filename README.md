# DM is a DJ
> Utility pack for organising music, FX effects and voice modulation for an RPG session

## Instructions
1. Install system dependencies (Debian / Ubuntu / Linux Mint).
```bash
sudo apt update

# audio backend & tools
sudo apt install -y pipewire pipewire-pulse pulseaudio-utils

# audio playback
sudo apt install -y mpv alsa-utils

# LADSPA plugins (voice effects)
sudo apt install -y swh-plugins tap-plugins

# optional: for recording / monitoring
sudo apt install -y pavucontrol
```

2. Setup audio channnels:
```bash
./run_setup.sh
```
If you want to do it differently, just create your own mix sink and update `.env` accordingly.

3. Fill `.env` file.

To check `MIC_SOURCE` run:
```bash
pactl list short sources
```
To check `SPEAKER_SINK` run:
```bash
pactl list short sinks
```
To decrease mic sensitivity run:
```bash
pactl set-source-volume \
  $MIC_SOURCE 60%
```

4. Organise your tracks inside the `/data` folder, e.g.:
```bash
- data/
    -- music/
        --- location_1/
            ---- track_1.mp3
        --- location_2/
            ---- track_1.mp3
    -- ambient/
        --- wind.mp3
    -- fx/
        --- thunder.mp3
```
The `music`, `ambient` and `fx` folders must keep their names as they're representing 3 different channels.

5. Install requirements.
```bash
pip install -r requirements.txt
```

6. Run server.
```bash
./run_server.sh
```

7. Cleanup after having good time.
```bash
./run_cleanup.sh
```
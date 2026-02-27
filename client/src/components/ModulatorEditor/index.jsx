import { useState } from "react";
import { useHTTPAudio } from "../../context/HTTPContext";
import "./index.css";

const DEFAULT_EFFECT = {
  name: "",
  gain: 0.0,
  drive: 0.0,
  tone: 0.0,
  mix: 0.0,
  pitch: 0.0,
  chorus: 0.0,
  delay: 0.0,
  reverb: 0.0,
  ring_mod: 0.0,
  bitcrusher: 0.0,
  low_pass: 0.0,
  high_pass: 0.0,
  tremolo: 0.0,
};

const PARAMS = [
  { key: "gain", label: "Gain", min: 0, max: 10, step: 0.01 },
  { key: "drive", label: "Drive", min: 0, max: 1, step: 0.01 },
  { key: "tone", label: "Tone", min: 0, max: 1, step: 0.01 },
  { key: "mix", label: "Mix", min: 0, max: 1, step: 0.01 },
  { key: "pitch", label: "Pitch", min: -36, max: 36, step: 1 },
  { key: "chorus", label: "Chorus", min: 0, max: 1, step: 0.01 },
  { key: "delay", label: "Delay (ms)", min: 0, max: 500, step: 1 },
  { key: "reverb", label: "Reverb", min: 0, max: 1, step: 0.01 },
  { key: "ring_mod", label: "Ring Mod (Hz)", min: 0, max: 2000, step: 1 },
  { key: "bitcrusher", label: "Bitcrusher", min: 0, max: 1, step: 0.01 },
  { key: "low_pass", label: "Low Pass (Hz)", min: 0, max: 20000, step: 10 },
  { key: "high_pass", label: "High Pass (Hz)", min: 0, max: 20000, step: 10 },
  { key: "tremolo", label: "Tremolo (Hz)", min: 0, max: 20, step: 0.1 },
];

export default function EffectEditor() {
  const [effect, setEffect] = useState(DEFAULT_EFFECT);
  const [selectedPreset, setSelectedPreset] = useState("");

  const {
    tracks,
    setCustomEffect,
    saveVoiceEffect
  } = useHTTPAudio();

  const modulatorEffects = tracks?.modulator ?? {};

  const updateValue = (key, value) => {
    setEffect((prev) => ({
      ...prev,
      [key]: Number(value),
    }));
  };

  const handlePresetChange = (e) => {
    const presetName = e.target.value;
    setSelectedPreset(presetName);

    if (!presetName) {
      setEffect(DEFAULT_EFFECT);
      return;
    }

    // Handle "off" preset
    if (presetName === "off") {
      setEffect(DEFAULT_EFFECT);
      // Call setCustomEffect with all zeros to turn off effects
      setCustomEffect({
        gain: 0,
        drive: 0,
        tone: 0,
        mix: 0,
        pitch: 0,
        chorus: 0,
        delay: 0,
        reverb: 0,
        ring_mod: 0,
        bitcrusher: 0,
        low_pass: 0,
        high_pass: 0,
        tremolo: 0,
      });
      return;
    }

    const presetValues = modulatorEffects[presetName];
    if (!presetValues) return;

    setEffect({
      ...DEFAULT_EFFECT,
      ...presetValues,
      name: presetName,
    });
  };

  const handlePlay = () => {
    const { name, ...params } = effect;
    setCustomEffect(params);
  };

  const handleSave = async () => {
    if (!effect.name.trim()) return;
    await saveVoiceEffect(effect.name);
    setSelectedPreset(effect.name);
  };

  return (
    <div className="editor">
      <h2>Voice Effect</h2>

      {/* Preset selector */}
      <label className="preset-field">
        Base preset
        <select value={selectedPreset} onChange={handlePresetChange}>
          <option value="">— Select preset —</option>
          <option value="off">Off (no effects)</option>
          {Object.keys(modulatorEffects).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      {/* Name */}
      <label className="name-field">
        Effect Name
        <input
          type="text"
          value={effect.name}
          onChange={(e) =>
            setEffect((prev) => ({ ...prev, name: e.target.value }))
          }
          placeholder="New effect"
        />
      </label>

      {/* Sliders */}
      <div className="sliders">
        {PARAMS.map(({ key, label, min, max, step }) => (
          <div className="slider-row" key={key}>
            <label>
              {label}
            </label>
            <div className="slider-input-group">
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={effect[key]}
                onChange={(e) => updateValue(key, e.target.value)}
              />
              <input
                type="number"
                min={min}
                max={max}
                step={step}
                value={effect[key]}
                onChange={(e) => {
                  let val = Number(e.target.value);
                  if (val < min) val = min;
                  if (val > max) val = max;
                  updateValue(key, val);
                }}
                className="number-input"
              />
            </div>
          </div>
        ))}
      </div>


      {/* Actions */}
      <div className="actions">
        <button className="play-button" onClick={handlePlay}>
          ▶ Play
        </button>

        <button className="save-button" onClick={handleSave}>
          Save
        </button>
      </div>
    </div>
  );
}
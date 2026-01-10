import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { createContext, useContext, useState, useCallback, useEffect } from "react";

const HTTPAudioContext = createContext();
export const useHTTPAudio = () => useContext(HTTPAudioContext);

export const HTTPAudioProvider = ({ children }) => {
  const [loading, setLoading] = useState(true); // general loading
  const [requestLoading, setRequestLoading] = useState({}); // per-request loading
  const [tracks, setTracks] = useState({ music: [], ambient: [], fx: [] });

  const API_BASE = process.env.REACT_APP_API?.replace(/\/$/, "");
  if (!API_BASE) console.warn("REACT_APP_API is not defined in your .env file!");

  // ---------------------
  // Helpers to send query params safely
  // ---------------------
  const setRequestBusy = (key, busy) => {
    setRequestLoading((prev) => ({ ...prev, [key]: busy }));
  };

  const get = useCallback(
    async (path, key) => {
      if (!API_BASE) throw new Error("API_BASE is not set");
      if (key) setRequestBusy(key, true);
      try {
        const res = await fetch(new URL(path, API_BASE).toString(), { method: "GET" });
        if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
        return await res.json();
      } finally {
        if (key) setRequestBusy(key, false);
      }
    },
    [API_BASE]
  );

  const postWithQuery = useCallback(
    async (path, params = {}, key) => {
      if (!API_BASE) throw new Error("API_BASE is not set");
      if (key) setRequestBusy(key, true);
      try {
        const url = new URL(path, API_BASE);
        Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
        const res = await fetch(url.toString(), { method: "POST" });
        if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
        return await res.json();
      } finally {
        if (key) setRequestBusy(key, false);
      }
    },
    [API_BASE]
  );

  const putWithQuery = useCallback(
    async (path, params = {}, key) => {
      if (!API_BASE) throw new Error("API_BASE is not set");
      if (key) setRequestBusy(key, true);
      try {
        const url = new URL(path, API_BASE);
        Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
        const res = await fetch(url.toString(), { method: "PUT" });
        if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`);
        return await res.json();
      } finally {
        if (key) setRequestBusy(key, false);
      }
    },
    [API_BASE]
  );

  const delWithQuery = useCallback(
    async (path, params = {}, key) => {
      if (!API_BASE) throw new Error("API_BASE is not set");
      if (key) setRequestBusy(key, true);
      try {
        const url = new URL(path, API_BASE);
        Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
        const res = await fetch(url.toString(), { method: "DELETE" });
        if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
        return await res.json();
      } finally {
        if (key) setRequestBusy(key, false);
      }
    },
    [API_BASE]
  );

  // ---------------------
  // TRACK LISTS
  // ---------------------
  const getMusicTracks = useCallback(() => get("/tracks/music", "tracks_music"), [get]);
  const getAmbientTracks = useCallback(() => get("/tracks/ambient", "tracks_ambient"), [get]);
  const getFxTracks = useCallback(() => get("/tracks/fx", "tracks_fx"), [get]);
  const listVoiceEffects = useCallback(() => get("/modulator", "modulator_list"), [get]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [musicRes, ambientRes, fxRes, voiceRes] = await Promise.all([
          getMusicTracks(),
          getAmbientTracks(),
          getFxTracks(),
          listVoiceEffects()
        ]);
        setTracks({
          music: musicRes || [],
          ambient: ambientRes || [],
          fx: fxRes || [],
          modulator: voiceRes
        });
      } catch (error) {
        console.error("Failed to fetch all tracks:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [getMusicTracks, getAmbientTracks, getFxTracks, listVoiceEffects]);

  // ---------------------
  // MUSIC
  // ---------------------
  const playMusic = useCallback((track) => postWithQuery("/music/play", { track }, "music_play"), [postWithQuery]);
  const stopMusic = useCallback(() => postWithQuery("/music/stop", {}, "music_stop"), [postWithQuery]);
  const setMusicVolume = useCallback((volume) => postWithQuery("/music/volume", { volume }, "music_volume"), [postWithQuery]);
  const setMusicCrossfadeTime = useCallback((crossfade_time) => postWithQuery("/music/crossfade_time", { crossfade_time }, "music_crossfade"), [postWithQuery]);
  const setMusicLoopMode = useCallback((mode) => postWithQuery("/music/loop_mode", { mode }, "music_loop"), [postWithQuery]);

  // ---------------------
  // AMBIENT
  // ---------------------
  const playAmbient = useCallback((track) => postWithQuery("/ambient/play", { track }, "ambient_play"), [postWithQuery]);
  const stopAmbient = useCallback(() => postWithQuery("/ambient/stop", {}, "ambient_stop"), [postWithQuery]);
  const setAmbientVolume = useCallback((volume) => postWithQuery("/ambient/volume", { volume }, "ambient_volume"), [postWithQuery]);
  const setAmbientCrossfadeTime = useCallback((crossfade_time) => postWithQuery("/ambient/crossfade_time", { crossfade_time }, "ambient_crossfade"), [postWithQuery]);
  const setAmbientLoopMode = useCallback((mode) => postWithQuery("/ambient/loop_mode", { mode }, "ambient_loop"), [postWithQuery]);

  // ---------------------
  // FX
  // ---------------------
  const playFx = useCallback((track) => postWithQuery("/fx/play", { track }, "fx_play"), [postWithQuery]);
  const setFxVolume = useCallback((volume) => postWithQuery("/fx/volume", { volume }, "fx_volume"), [postWithQuery]);

  // ---------------------
  // VOICE MODULATOR
  // ---------------------
  const loadVoiceEffect = useCallback((effect) => postWithQuery("/modulator", { effect }, "modulator_load"), [postWithQuery]);
  const setCustomEffect = useCallback((params) => postWithQuery("/modulator/custom", params, "modulator_custom"), [postWithQuery]);
  const saveVoiceEffect = useCallback((name) => putWithQuery("/modulator", { name }, "modulator_save"), [putWithQuery]);
  const deleteVoiceEffect = useCallback((name) => delWithQuery("/modulator", { name }, "modulator_delete"), [delWithQuery]);

  // ---------------------
  // Refetch helper
  // ---------------------
  const refetch = {
    musicTracks: getMusicTracks,
    ambientTracks: getAmbientTracks,
    fxTracks: getFxTracks,
    voiceEffects: listVoiceEffects,
  };

  if (loading) return <FontAwesomeIcon icon="spinner" spin />;

  return (
    <HTTPAudioContext.Provider
      value={{
        loading,
        requestLoading, // expose per-request loading
        tracks,
        refetch,
        // music
        playMusic,
        stopMusic,
        setMusicVolume,
        setMusicCrossfadeTime,
        setMusicLoopMode,
        // ambient
        playAmbient,
        stopAmbient,
        setAmbientVolume,
        setAmbientCrossfadeTime,
        setAmbientLoopMode,
        // fx
        playFx,
        setFxVolume,
        // voice
        listVoiceEffects,
        loadVoiceEffect,
        setCustomEffect,
        saveVoiceEffect,
        deleteVoiceEffect,
        // raw tracks
        getMusicTracks,
        getAmbientTracks,
        getFxTracks,
      }}
    >
      {children}
    </HTTPAudioContext.Provider>
  );
};

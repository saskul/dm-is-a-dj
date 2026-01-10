// src/state/NavbarContext.js
import { createContext, useContext, useRef, useState } from "react";
import { useHTTPAudio } from "./HTTPContext";
import { useWS } from "./WSContext";

const NavbarContext = createContext();
export const useNavbar = () => useContext(NavbarContext);

const HOLD_TIME = 500;

export const NavbarProvider = ({ children }) => {
  const {
    stopMusic,
    stopAmbient,
    loadVoiceEffect
  } = useHTTPAudio();

  const { state: wsState } = useWS();

  // local loading + volume memory
  const [loading, setLoading] = useState({
    music: false,
    ambient: false,
    voice: false,
  });

  const holdTimer = useRef(null);
  const wasHeld = useRef(false);

  // -------------------------
  // DERIVED CHANNEL STATES
  // -------------------------
  const channels = {
    music: loading.music
      ? "loading"
      : !wsState.music.track
      ? "off"
      : "on",

    ambient: loading.ambient
      ? "loading"
      : !wsState.ambient.track
      ? "off"
      : "on",

    fx: "off",

    voice: loading.voice
      ? "loading"
      : wsState.modulator?.effect === "off"
      ? "off"
      : "on",
  };

  // -------------------------
  // SCROLL
  // -------------------------
  const scrollToSection = (channel) => {
    const element = document.getElementById(`section-${channel}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // -------------------------
  // VOLUME MUTE / UNMUTE
  // -------------------------
  const toggleMute = async (channel) => {
    if (channel === "fx") return;

    setLoading((l) => ({ ...l, [channel]: true }));

    try {
      if (channel === "music") {
        if (wsState.music?.playing) {
          await stopMusic();
        } else {
          scrollToSection("music");
        }
      }

      if (channel === "ambient") {
        if (wsState.ambient?.playing) {
          await stopAmbient();
        } else {
          scrollToSection("ambient");
        }
      }

      if (channel === "voice") {
        if (wsState.modulator?.effect !== "off") {
          await loadVoiceEffect("off");
        } else {
          scrollToSection("voice");
        }
      }
    } finally {
      setLoading((l) => ({ ...l, [channel]: false }));
    }
  };

  // -------------------------
  // PRESS HANDLERS
  // -------------------------
  const onPressStart = (channel) => {
    wasHeld.current = false;

    if (channel === "fx") return;

    holdTimer.current = setTimeout(() => {
      wasHeld.current = true;
      toggleMute(channel);
    }, HOLD_TIME);
  };

  const onPressEnd = (channel) => {
    clearTimeout(holdTimer.current);

    if (!wasHeld.current) {
      scrollToSection(channel);
    }
  };

  return (
    <NavbarContext.Provider
      value={{
        channels,
        onPressStart,
        onPressEnd,
      }}
    >
      {children}
    </NavbarContext.Provider>
  );
};

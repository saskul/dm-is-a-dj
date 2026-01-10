import React, { createContext, useContext, useEffect, useState } from "react";

const WSContext = createContext();

export const useWS = () => useContext(WSContext);

export const WSProvider = ({ children }) => {
  const [state, setState] = useState({
    music: {},
    ambient: {},
    modulator: {},
    fx: {},
  });

  const [connected, setConnected] = useState(false);

  const API_BASE = process.env.REACT_APP_API?.replace(/\/$/, "");

  useEffect(() => {
    if (!API_BASE) return;

    let socket;
    let reconnectTimeout;

    const connect = () => {
      const wsBase = API_BASE.replace(/^http/, "ws");
      socket = new WebSocket(`${wsBase}/ws`);

      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        reconnectTimeout = setTimeout(connect, 2000);
      };
      socket.onerror = (e) => console.error("WebSocket error", e);

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setState((prev) => ({ ...prev, ...data }));
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      socket?.close();
    };
  }, [API_BASE]);

  return (
    <WSContext.Provider value={{ state, connected }}>
      {children}
    </WSContext.Provider>
  );
};

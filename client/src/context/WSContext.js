import React, { createContext, useContext, useEffect, useState } from "react";
import isEqual from "lodash/isEqual";

const REACT_APP_API = window.REACT_APP_API || process.env.REACT_APP_API;
const API_BASE = REACT_APP_API?.replace(/\/$/, "");

const mergeIfChanged = (prev, data) => {
  const next = {
    ...prev,
    ...data
  };

  return isEqual(prev, next) ? prev : next;
};

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

  useEffect(() => {
    if (!API_BASE) return;

    let socket;
    let reconnectTimeout;

    const connect = () => {
      const wsBase = API_BASE.replace(/^http/, "ws");
      socket = new WebSocket(`${wsBase}/ws`);

      socket.onopen = () => {
        setConnected((prev) => (prev ? prev : true));
      };

      socket.onclose = () => {
        setConnected((prev) => (!prev ? prev : false));
        reconnectTimeout = setTimeout(connect, 2000);
      };
      socket.onerror = (e) => console.error("WebSocket error", e);

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setState((prev) => mergeIfChanged(prev, data));
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      socket?.close();
    };
  }, [API_BASE]);

  const value = React.useMemo(
    () => ({ state, connected }),
    [state, connected]
  );

  return (
    <WSContext.Provider value={value}>
      {children}
    </WSContext.Provider>
  );
};

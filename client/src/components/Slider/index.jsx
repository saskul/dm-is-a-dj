import React, { useState, useEffect, useRef } from "react";
import "./index.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export const Slider = ({ 
  value = 0,
  onChange,
  debounceTime = 300, 
  isLoading = false,
  units = '%',
  header,
  min = 0,
  max = 100
}) => {
  const [localValue, setLocalValue] = useState(value);
  const timeoutRef = useRef(null);

  // compute percentage of the slider fill based on min/max
  const percent = ((localValue - min) / (max - min)) * 100;

  const handleChange = (e) => {
    const newLocalValue = parseFloat(e.target.value);
    setLocalValue(newLocalValue);

    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    timeoutRef.current = setTimeout(() => {
      onChange?.(newLocalValue);
    }, debounceTime);
  };

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  return (
    <div className='volume-slider-wrapper'>
      {header && <h3>{header}</h3>}
      <div className="volume-slider-container">
        <input
          type="range"
          min={min}
          max={max}
          value={localValue}
          onChange={handleChange}
          className="volume-slider"
          style={{ "--value": percent }}
        />
        <span className="volume-label noselect">
          {isLoading ? (
            <FontAwesomeIcon icon='spinner' spin={true} />
          ) : (
            <div>{localValue}{units}</div>
          )}
        </span>
      </div>
    </div>
  );
};

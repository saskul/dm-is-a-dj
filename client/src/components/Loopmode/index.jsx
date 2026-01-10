import { useState } from "react";
import './index.css';

export const LoopModeDropdown = ({ value = null, onChange }) => {
  const options = [
    { label: "Off", value: "off" },
    { label: "Track", value: "track" },
    { label: "Folder", value: "list" },
  ];

  const [open, setOpen] = useState(false);

  const handleSelect = (val) => {
    onChange?.(val);
    setOpen(false);
  };

  return (
    <div className='loopmode-dropdown_wrapper'>
        <h3>Loopmode</h3>
        <div className="loopmode-dropdown">
        <div className="selected" onClick={() => setOpen((prev) => !prev)}>
            {options.find(o => o.value === value)?.label || "Select loop mode"} ▾
        </div>
        {open && (
            <ul className="options">
            {options.map((o) => (
                <li
                key={o.value ?? "off"}
                className={o.value === value ? "selected-option" : ""}
                onClick={() => handleSelect(o.value)}
                >
                {o.label}
                </li>
            ))}
            </ul>
        )}
        </div>
    </div>
  );
};

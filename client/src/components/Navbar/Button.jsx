import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useNavbar } from "../../context/NavbarContext";
import "./index.css";

const Button = ({ channel, icon }) => {
  const { channels, onPressStart, onPressEnd } = useNavbar();
  const state = channels[channel];

  const handleTouchStart = (e) => {
    onPressStart(channel);
  };

  const handleTouchEnd = (e) => {
    onPressEnd(channel);
  };

  return (
    <button
      className={`nav-btn ${state} noselect`}
      onMouseDown={() => onPressStart(channel)}
      onMouseUp={() => onPressEnd(channel)}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchEnd}
    >
      <FontAwesomeIcon icon={icon} spin={state === "loading"} />
    </button>
  );
};

export default Button;
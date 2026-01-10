import Button from './Button';
import "./index.css";

const Navbar = () => {
  return (
    <nav className="navbar">
      <Button channel="music" icon="music" />
      <Button channel="ambient" icon="tree" />
      <Button channel="fx" icon="bolt" />
      <Button channel="voice" icon="microphone" />
    </nav>
  );
};

export default Navbar;

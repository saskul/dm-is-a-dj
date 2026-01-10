import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useState } from "react";
import './index.css';
import { Slider } from "../Slider";
import { LoopModeDropdown } from "../Loopmode";

function buildTree(paths) {
  const root = {};

  paths.forEach((path) => {
    const parts = path.split("/");
    let current = root;

    parts.forEach((part, index) => {
      if (!current[part]) {
        current[part] = index === parts.length - 1 ? path : {};
      }
      current = current[part];
    });
  });

  return root;
}

const TreeNode = ({ node, name, onClick, currentTrack, loopMode, parentPath = "" }) => {
  const [expanded, setExpanded] = useState(false);

  const isFolder = typeof node === "object";

  const handleToggle = () => setExpanded((prev) => !prev);

  const fullPath = parentPath ? `${parentPath}/${name}` : name;

  let highlight = false;
  let dim = false;

  if (!isFolder && node === currentTrack) {
    highlight = true;
  }

  if (!isFolder && loopMode === "list" && currentTrack?.startsWith(parentPath + "/") && node !== currentTrack) {
    dim = true;
  }

  if (isFolder && loopMode === "list" && currentTrack?.startsWith(fullPath + "/")) {
    dim = true;
  }

  if (isFolder) {
    return (
      <div className={`folder ${dim ? "dim" : ""}`}>
        <div onClick={handleToggle}>
          {expanded ? (
            <FontAwesomeIcon icon='folder-open' />
          ) : (
            <FontAwesomeIcon icon='folder' />
          )} {name}
        </div>
        {expanded &&
          Object.keys(node).map((key) => (
            <TreeNode
              key={key}
              node={node[key]}
              name={key}
              onClick={onClick}
              currentTrack={currentTrack}
              loopMode={loopMode}
              parentPath={fullPath}
            />
          ))}
      </div>
    );
  } else {
    return (
      <div
        className={`track ${highlight ? "highlight" : ""} ${dim ? "dim" : ""}`}
        onClick={() => onClick(node)}
      >
        <FontAwesomeIcon icon='music' /> {name}
      </div>
    );
  }
};

export const PlaylistExplorer = ({
  files,
  onFileClick,
  volume,
  onVolumeChange,
  track,
  crossfade,
  onCrossfadeChange,
  loopMode = null, // null | 'track' | 'list',
  onLoopModeChange,
  hasLoopMode = false,
  hasCrossfade = false,
  noControls=false
}) => {
  const tree = buildTree(files);

  return (
    <div className='playlist_wrapper'>
      {!noControls && (
        <div>
          <div className={!hasLoopMode && !hasCrossfade ? 'playlist_control-only' : 'playlist_control'}>
            <Slider value={volume} onChange={onVolumeChange} header='Volume' />
          </div>
          {hasCrossfade && (
            <div className='playlist_control'>
              <Slider value={crossfade} onChange={onCrossfadeChange} header='Crossfade' units='s' max={10} />
            </div>
          )}
          {hasLoopMode && (
            <div className='playlist_control'>
              <LoopModeDropdown
                value={loopMode}
                onChange={onLoopModeChange}
              />
            </div>
          )}
        </div>
      )}


      <div className='playlist'>
        {Object.keys(tree).map((key) => (
          <TreeNode
            key={key}
            node={tree[key]}
            name={key}
            onClick={onFileClick}
            currentTrack={track}
            loopMode={loopMode}
          />
        ))}
      </div>
    </div>
  );
};

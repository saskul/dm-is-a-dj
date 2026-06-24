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

const isNumber = (value) =>
  typeof value === "number" && Number.isFinite(value);

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
};

const TrackProgress = ({ position, duration }) => {
  if (!isNumber(position) || !isNumber(duration) || duration <= 0) {
    return null;
  }

  const progress = Math.min(Math.max(position / duration, 0), 1);

  return (
    <div className="track-progress">
      <span>{formatTime(position)}</span>

      <div className="track-progress-line">
        <div
          className="track-progress-fill"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <span>{formatTime(duration)}</span>
    </div>
  );
};

const TreeNode = ({
  node,
  name,
  onClick,
  onDelete,
  currentTrack,
  loopMode,
  position,
  duration,
  parentPath = ""
}) => {
  const [expanded, setExpanded] = useState(false);

  const isFolder = typeof node === "object";
  const fullPath = parentPath ? `${parentPath}/${name}` : name;

  const handleToggle = () => setExpanded((prev) => !prev);

  const handleDelete = (e) => {
    e.stopPropagation();
    onDelete?.(fullPath);
  };

  let highlight = false;
  let dim = false;

  if (!isFolder && node === currentTrack) {
    highlight = true;
  }

  if (
    !isFolder &&
    loopMode === "list" &&
    currentTrack?.startsWith(parentPath + "/") &&
    node !== currentTrack
  ) {
    dim = true;
  }

  if (isFolder && loopMode === "list" && currentTrack?.startsWith(fullPath + "/")) {
    dim = true;
  }

  if (isFolder) {
    return (
      <div className={`folder ${dim ? "dim" : ""}`}>
        <div className="folder-row" onClick={handleToggle}>
          {expanded ? (
            <FontAwesomeIcon icon="folder-open" />
          ) : (
            <FontAwesomeIcon icon="folder" />
          )}
          <span className="name">{name}</span>

          {onDelete && (
            <FontAwesomeIcon
              icon="trash"
              className="delete-icon"
              onClick={handleDelete}
            />
          )}
        </div>

        {expanded &&
          Object.keys(node).map((key) => (
            <TreeNode
              key={key}
              node={node[key]}
              name={key}
              onClick={onClick}
              onDelete={onDelete}
              currentTrack={currentTrack}
              loopMode={loopMode}
              position={position}
              duration={duration}
              parentPath={fullPath}
            />
          ))}
      </div>
    );
  }

  return (
    <div
      className={`track ${highlight ? "highlight" : ""} ${dim ? "dim" : ""}`}
      onClick={() => onClick(node)}
    >
      <FontAwesomeIcon icon="music" />
      <span className="name">{name}</span>
      {highlight && (
        <TrackProgress position={position} duration={duration} />
      )}

      {onDelete && (
        <FontAwesomeIcon
          icon="trash"
          className="delete-icon"
          onClick={handleDelete}
        />
      )}
    </div>
  );
};

export const PlaylistExplorer = ({
  files,
  onFileClick,
  onDelete,
  volume,
  onVolumeChange,
  track,
  crossfade,
  onCrossfadeChange,
  loopMode = null,
  onLoopModeChange,
  hasLoopMode = false,
  hasCrossfade = false,
  noControls = false,
  position = null,
  duration = null
}) => {
  const tree = buildTree(files);

  return (
    <div className="playlist_wrapper">
      {!noControls && (
        <div>
          <div
            className={
              !hasLoopMode && !hasCrossfade
                ? "playlist_control-only"
                : "playlist_control"
            }
          >
            <Slider value={volume} onChange={onVolumeChange} header="Volume" />
          </div>

          {hasCrossfade && (
            <div className="playlist_control">
              <Slider
                value={crossfade}
                onChange={onCrossfadeChange}
                header="Crossfade"
                units="s"
                max={20}
              />
            </div>
          )}

          {hasLoopMode && (
            <div className="playlist_control">
              <LoopModeDropdown
                value={loopMode}
                onChange={onLoopModeChange}
              />
            </div>
          )}
        </div>
      )}

      <div className="playlist">
        {Object.keys(tree).map((key) => (
          <TreeNode
            key={key}
            node={tree[key]}
            name={key}
            onClick={onFileClick}
            onDelete={onDelete}
            currentTrack={track}
            loopMode={loopMode}
            position={position}
            duration={duration}
          />
        ))}
      </div>
    </div>
  );
};

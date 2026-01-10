import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function Modulator () {
    const { 
        tracks,
        loadVoiceEffect,
    } = useHTTPAudio();
    const { state } = useWS();
    const files = tracks.modulator;

    const { modulator } = state;

    const {
        effect,
    } = modulator;

    return (
        <PlaylistExplorer 
            track={effect}
            files={files}
            onFileClick={loadVoiceEffect}
            noControls
        />
    );
}

export default Modulator;
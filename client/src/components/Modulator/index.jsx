import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function Modulator () {
    const { 
        tracks,
        requestLoading,
        loadVoiceEffect,
        setModulatorVolume
    } = useHTTPAudio();
    const { state } = useWS();
    const files = tracks.modulator;

    const { modulator } = state;

    const {
        effect,
        volume,
    } = modulator;

    const isVolumeLoading = !!requestLoading.modulator_volume;

    return (
        <PlaylistExplorer 
            track={effect}
            files={files}
            onFileClick={loadVoiceEffect}
            volume={volume}
            isVolumeLoading={isVolumeLoading}
            onVolumeChange={setModulatorVolume}
        />
    );
}

export default Modulator;
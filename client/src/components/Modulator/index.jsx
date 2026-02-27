import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function Modulator () {
    const { 
        tracks,
        requestLoading,
        loadVoiceEffect,
        setModulatorVolume,
        deleteVoiceEffect
    } = useHTTPAudio();
    const { state } = useWS();
    const files = Object.keys(tracks.modulator);

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
            onDelete={deleteVoiceEffect}
        />
    );
}

export default Modulator;
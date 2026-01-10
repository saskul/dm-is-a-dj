import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function FX () {
    const { 
        tracks,
        requestLoading,
        playFx,
        setFxVolume,
    } = useHTTPAudio();
    const { state } = useWS();
    const files = tracks.fx;

    const { fx } = state;

    const {
        track,
        volume,
    } = fx;

    const isVolumeLoading = !!requestLoading.fx_volume;

    return (
        <PlaylistExplorer 
            track={track}
            files={files}
            onFileClick={playFx}
            volume={volume}
            isVolumeLoading={isVolumeLoading}
            onVolumeChange={setFxVolume}
        />
    );
}

export default FX;
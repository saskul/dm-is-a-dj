import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function Ambient () {
    const { 
        tracks,
        requestLoading,
        playAmbient,
        setAmbientVolume,
        setAmbientLoopMode,
        setAmbientCrossfadeTime
    } = useHTTPAudio();
    const { state } = useWS();
    const files = tracks.ambient;

    const { ambient } = state;

    const {
        crossfade_time,
        loop_mode,
        track,
        volume,
    } = ambient;

    const isVolumeLoading = !!requestLoading.ambient_volume;

    return (
        <PlaylistExplorer 
            track={track}
            files={files}
            onFileClick={playAmbient}
            volume={volume}
            isVolumeLoading={isVolumeLoading}
            onVolumeChange={setAmbientVolume}
            loopMode={loop_mode}
            onLoopModeChange={setAmbientLoopMode}
            crossfade={crossfade_time}
            onCrossfadeChange={setAmbientCrossfadeTime}
            hasLoopMode
            hasCrossfade
        />
    );
}

export default Ambient;
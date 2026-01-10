import { PlaylistExplorer } from "../Playlist";
import { useHTTPAudio  } from "../../context/HTTPContext";
import { useWS } from "../../context/WSContext";

function Music () {
    const { 
        tracks,
        requestLoading,
        playMusic,
        setMusicVolume,
        setMusicLoopMode,
        setMusicCrossfadeTime
    } = useHTTPAudio();
    const { state } = useWS();
    const files = tracks.music;

    const { music } = state;

    const {
        crossfade_time,
        loop_mode,
        track,
        volume,
    } = music;

    const isVolumeLoading = !!requestLoading.music_volume;

    return (
        <PlaylistExplorer 
            track={track}
            files={files}
            onFileClick={playMusic}
            volume={volume}
            isVolumeLoading={isVolumeLoading}
            onVolumeChange={setMusicVolume}
            loopMode={loop_mode}
            onLoopModeChange={setMusicLoopMode}
            crossfade={crossfade_time}
            onCrossfadeChange={setMusicCrossfadeTime}
            hasLoopMode
            hasCrossfade
        />
    );
}

export default Music;
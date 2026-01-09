import socket
import os

def get_local_ip():
    """
    Returns the machine's IP in the local network.
    """
    try:
        # create a dummy socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # connect to a public IP (does not send packets)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
    

def list_audio_files(root_dir: str, extensions=None):
    """
    Recursively lists audio files in a directory.
    
    :param root_dir: path to search
    :param extensions: list of file extensions to include
    :return: list of relative paths
    """
    if extensions is None:
        extensions = [".mp3", ".wav", ".ogg", ".flac"]

    result = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if any(f.lower().endswith(ext) for ext in extensions):
                # store path relative to root_dir
                rel_path = os.path.relpath(os.path.join(dirpath, f), root_dir)
                result.append(rel_path)
    return result
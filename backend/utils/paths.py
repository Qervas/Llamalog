from pathlib import Path
import os

def get_project_root() -> Path:
    """Get absolute path to project root from any location"""
    current_file = Path(__file__).resolve()  # Get this file's location
    # Go up until we find the project root (where llama.cpp, backend, etc. are)
    current_dir = current_file.parent
    while current_dir.name != "backend":
        current_dir = current_dir.parent
    return current_dir.parent

def ensure_path(path: Path) -> Path:
    """Ensure a path exists and create it if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)
    return path

# Common paths
PROJECT_ROOT = get_project_root()
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = ensure_path(BACKEND_DIR / "data")
MODELS_DIR = PROJECT_ROOT / "llama.cpp" / "models"
LLAMA_SERVER = PROJECT_ROOT / "llama.cpp" / "build" / "bin" / "llama-server"
if os.name == 'nt':  # Windows
    LLAMA_SERVER = LLAMA_SERVER.with_suffix('.exe')

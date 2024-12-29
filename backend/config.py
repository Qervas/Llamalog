from pathlib import Path
from pydantic import BaseModel
from utils.paths import PROJECT_ROOT, DATA_DIR, MODELS_DIR, LLAMA_SERVER
import os
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

class Settings(BaseModel):
    # Base paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = DATA_DIR

    # Model settings
    MODELS_DIR: Path = MODELS_DIR
    LLAMA_SERVER_PATH: Path = LLAMA_SERVER

    # Database settings
    DB_PATH: Path = DATA_DIR / "chat_history.db"
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"

    # Server settings
    LLAMA_SERVER_HOST: str = os.getenv('LLAMA_SERVER_HOST', '127.0.0.1')
    LLAMA_SERVER_PORT: int = int(os.getenv('LLAMA_SERVER_PORT', '8080'))

    def validate_paths(self):
        """Validate that all required paths exist"""
        if not self.MODELS_DIR.exists():
            raise FileNotFoundError(f"Models directory not found at: {self.MODELS_DIR}")

        if not self.LLAMA_SERVER_PATH.exists():
            raise FileNotFoundError(f"LLama server not found at: {self.LLAMA_SERVER_PATH}")

        # Ensure data directory exists
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    class Config:
        arbitrary_types_allowed = True  # Allow Path objects

# Create settings instance
settings = Settings()

# Create default .env file if it doesn't exist
def create_default_env():
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(f"""# Server Configuration
LLAMA_SERVER_HOST=127.0.0.1
LLAMA_SERVER_PORT=8080

# Database Configuration
DATABASE_URL=sqlite:///{settings.DB_PATH}

# Model Configuration
MODELS_DIR={settings.MODELS_DIR}
LLAMA_SERVER_PATH={settings.LLAMA_SERVER_PATH}
""")

# Create default .env file
create_default_env()

# Validate paths on import
try:
    settings.validate_paths()
except Exception as e:
    print(f"Warning: Configuration validation failed: {e}")

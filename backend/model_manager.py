import os
from typing import Dict, List, Optional
import json
import httpx
import asyncio
import time
from dataclasses import dataclass
from config import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    name: str
    path: str
    size: str
    loaded: bool = False
    type: str = "GGUF"
    description: str = ""
    parameters: str = ""
    context_length: int = 4096
    requirements: Dict = None

class ModelManager:
    def __init__(self):
        self.models_dir = settings.MODELS_DIR
        self.models: Dict[str, ModelInfo] = {}
        self.current_model: Optional[str] = None
        self.llama_server_path = settings.LLAMA_SERVER_PATH
        self.llama_server_url = f"http://{settings.LLAMA_SERVER_HOST}:{settings.LLAMA_SERVER_PORT}"
        self.llama_server_process = None
        self.scan_models()

    def scan_models(self):
        """Scan the models directory for available models."""
        self.models.clear()
        try:
            for filename in os.listdir(self.models_dir):
                if filename.endswith('.gguf'):
                    path = os.path.join(self.models_dir, filename)
                    size = self._get_file_size(path)
                    name = filename.replace('.gguf', '')

                    # Try to load metadata if exists
                    metadata = self._load_model_metadata(name)

                    self.models[name] = ModelInfo(
                        name=name,
                        path=path,
                        size=size,
                        description=metadata.get('description', ''),
                        parameters=metadata.get('parameters', 'Unknown'),
                        context_length=metadata.get('context_length', 4096),
                        requirements=metadata.get('requirements', {})
                    )
        except Exception as e:
            logger.error(f"Error scanning models: {str(e)}")

    def _get_file_size(self, path: str) -> str:
        """Get human-readable file size."""
        size = os.path.getsize(path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _load_model_metadata(self, model_name: str) -> Dict:
        """Load model metadata from JSON file if exists."""
        try:
            metadata_path = os.path.join(self.models_dir, f"{model_name}.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading model metadata: {str(e)}")
        return {}

    async def load_model(self, model_name: str) -> bool:
        """Load a model into the llama.cpp server."""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        model = self.models[model_name]
        if model.loaded:
            return True

        # Stop current model if any
        await self.stop_model()

        try:
            # Build command with proper path handling
            model_path = self.models_dir / f"{model_name}.gguf"
            cmd = [
                str(self.llama_server_path),
                "-m", str(model_path),
                "-c", str(model.context_length),
                "--host", settings.LLAMA_SERVER_HOST,
                "--port", str(settings.LLAMA_SERVER_PORT),
                "--embedding",  # Enable embedding API
                "--port-emoji", str(settings.LLAMA_SERVER_PORT + 1),  # Additional port for emoji API
            ]

            logger.info(f"Starting llama.cpp server with command: {' '.join(cmd)}")

            # Start the server process
            self.llama_server_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for server to start (with timeout)
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        response = await client.get(f"{self.llama_server_url}/health")
                        if response.status_code == 200:
                            self.current_model = model_name
                            model.loaded = True
                            logger.info(f"Model {model_name} loaded successfully")
                            return True
                except:
                    await asyncio.sleep(1)
                    continue

            # If we get here, server didn't start properly
            await self.stop_model()
            raise Exception("Server failed to start within timeout period")

        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            await self.stop_model()
            return False

    async def stop_model(self):
        """Stop the currently running model."""
        if self.llama_server_process:
            try:
                # Try graceful shutdown first
                self.llama_server_process.terminate()
                try:
                    await asyncio.wait_for(self.llama_server_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown takes too long
                    self.llama_server_process.kill()
                    await self.llama_server_process.wait()

            except Exception as e:
                logger.error(f"Error stopping model: {str(e)}")
            finally:
                self.llama_server_process = None

        if self.current_model:
            if self.current_model in self.models:
                self.models[self.current_model].loaded = False
            self.current_model = None

    def get_available_models(self) -> List[Dict]:
        """Get list of available models and their status."""
        return [
            {
                "id": model.name,
                "name": model.name,
                "size": model.size,
                "loaded": model.loaded,
                "type": model.type,
                "description": model.description,
                "parameters": model.parameters,
                "context_length": model.context_length
            }
            for model in self.models.values()
        ]

    async def get_current_model(self) -> Dict:
        """Get current model status and information."""
        try:
            # Check if server is running and responding
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.llama_server_url}/health")
                if response.status_code == 200:
                    # Try to get model info from the server
                    try:
                        model_info = await client.get(f"{self.llama_server_url}/v1/models")
                        model_data = model_info.json()
                        if model_data and "model" in model_data:
                            # Update current_model if server reports it's loaded
                            model_name = model_data["model"].split("/")[-1].replace(".gguf", "")
                            self.current_model = model_name
                            if model_name in self.models:
                                self.models[model_name].loaded = True
                    except:
                        pass

                    if self.current_model:
                        model = self.models.get(self.current_model)
                        return {
                            "status": "running",
                            "model": {
                                "name": model.name,
                                "size": model.size,
                                "type": model.type,
                                "description": model.description,
                                "parameters": model.parameters,
                                "context_length": model.context_length
                            } if model else None
                        }
                    return {
                        "status": "running",
                        "model": None
                    }
        except Exception as e:
            logger.debug(f"Error checking current model: {str(e)}")

        return {
            "status": "stopped",
            "model": None
        }

    async def get_model_status(self) -> Dict:
        """Get current status of the model server and loaded model."""
        status = {
            "status": "stopped",
            "current_model": None,
            "available_models": self.get_available_models()
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.llama_server_url}/health")
                if response.status_code == 200:
                    status["status"] = "running"
                    if self.current_model:
                        model = self.models.get(self.current_model)
                        if model:
                            status["current_model"] = {
                                "name": model.name,
                                "size": model.size,
                                "type": model.type,
                                "description": model.description,
                                "parameters": model.parameters,
                                "context_length": model.context_length
                            }
        except Exception as e:
            logger.debug(f"Model status check failed: {str(e)}")

        return status

    async def _get_server_uptime(self) -> Optional[float]:
        """Get server uptime if available."""
        if not self.llama_server_process:
            return None

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.llama_server_url}/v1/metrics")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("uptime", None)
        except:
            pass

        return None

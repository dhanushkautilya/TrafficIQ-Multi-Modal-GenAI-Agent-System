"""Configuration management for TrafficIQ."""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Config(BaseSettings):
    """Application configuration from environment variables."""

    # Application
    environment: str = "development"
    log_level: str = "info"
    json_logging: bool = True
    debug: bool = False
    api_title: str = "TrafficIQ"
    api_version: str = "0.1.0"

    # GCP / Vertex AI
    use_vertex: bool = False
    gcp_project: Optional[str] = None
    gcp_region: str = "us-central1"
    vertex_endpoint_id: Optional[str] = None
    vertex_model_name: str = "gemma-3n-tuned-vehicles"

    # Storage
    artifacts_path: str = "./artifacts"
    use_gcs: bool = False
    gcs_bucket: Optional[str] = None

    # External Services
    bolo_service_url: str = "http://localhost:8001"
    bolo_api_key: str = "demo-key"
    case_service_url: str = "http://localhost:8002"
    case_api_key: str = "demo-key"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def setup_artifacts_dir(self) -> Path:
        """Ensure artifacts directory exists."""
        artifacts = Path(self.artifacts_path)
        artifacts.mkdir(parents=True, exist_ok=True)
        return artifacts

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config

"""
Configuration management for the backend
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///backend/cs2_market.db"
    
    # Application
    app_name: str = "CS2 Market Intelligence API"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_title: str = "CS2 Market Intelligence"
    api_version: str = "0.1.0"
    
    # Steam Integration
    # Steam Web API key from https://steamcommunity.com/dev/apikey
    # Daily limit: 100,000 calls per day (https://steamcommunity.com/dev/apiterms)
    # Used for: GetAssetClassInfo, GetSchemaItems, inventory lookups
    steam_api_key: Optional[str] = None
    cs2sh_api_key: Optional[str] = None
    frontend_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    
    # Security
    secret_key: str = "your-secret-key-for-sessions"  # Should be changed in production
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    def is_production(self) -> bool:
        """Return True when the app should avoid demo bootstrap behavior."""
        return self.environment.lower() in {"production", "prod"}

    def demo_bootstrap_enabled(self) -> bool:
        """
        Return True when synthetic catalog/history bootstrap should run.

        Demo and development environments keep the synthetic backfill available
        for local iteration, while production stays on the live collection path.
        """
        return not self.is_production()

settings = Settings()

"""
Configuration management for the backend
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/cs2_market"
    
    # Application
    app_name: str = "CS2 Market Intelligence API"
    environment: str = "development"
    debug: bool = True
    
    # API
    api_title: str = "CS2 Market Intelligence"
    api_version: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

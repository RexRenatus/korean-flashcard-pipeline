"""Configuration system for the CLI"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class ApiConfig(BaseModel):
    """API configuration settings"""
    provider: str = Field(default="openrouter", description="API provider")
    model: str = Field(default="anthropic/claude-3.5-sonnet", description="Model to use")
    base_url: str = Field(default="https://openrouter.ai/api/v1", description="API base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class ProcessingConfig(BaseModel):
    """Processing configuration settings"""
    max_concurrent: int = Field(default=20, ge=1, le=50, description="Maximum concurrent requests")
    batch_size: int = Field(default=100, description="Default batch size")
    rate_limit: Dict[str, int] = Field(
        default_factory=lambda: {
            "requests_per_minute": 60,
            "tokens_per_minute": 90000
        }
    )


class CacheConfig(BaseModel):
    """Cache configuration settings"""
    enabled: bool = Field(default=True, description="Enable caching")
    path: Path = Field(default=Path(".cache/flashcards"), description="Cache directory")
    ttl_days: int = Field(default=30, description="Cache TTL in days")
    max_size_gb: float = Field(default=10.0, description="Maximum cache size in GB")


class DatabaseConfig(BaseModel):
    """Database configuration settings"""
    path: Path = Field(default=Path("pipeline.db"), description="Database file path")
    connection_pool_size: int = Field(default=5, description="Connection pool size")
    enable_wal: bool = Field(default=True, description="Enable WAL mode")


class OutputConfig(BaseModel):
    """Output configuration settings"""
    default_format: str = Field(default="tsv", description="Default output format")
    anki: Dict[str, Any] = Field(
        default_factory=lambda: {
            "deck_name": "Korean Vocabulary",
            "tags": ["korean", "ai-generated"]
        }
    )
    quality: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_confidence": 0.8,
            "require_examples": True
        }
    )


class LoggingConfig(BaseModel):
    """Logging configuration settings"""
    level: str = Field(default="INFO", description="Log level")
    file: Optional[Path] = Field(default=Path("flashcard-pipeline.log"), description="Log file path")
    max_size_mb: int = Field(default=100, description="Maximum log file size in MB")
    retention_days: int = Field(default=7, description="Log retention in days")


class Config(BaseModel):
    """Main configuration class"""
    api: ApiConfig = Field(default_factory=ApiConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Plugin configuration
    plugins: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Custom presets
    presets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load configuration from YAML file"""
        if not path.exists():
            logger.warning(f"Configuration file {path} not found, using defaults")
            return cls()
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables
        env_mappings = {
            "FLASHCARD_API_KEY": ("api", "api_key"),
            "FLASHCARD_API_MODEL": ("api", "model"),
            "FLASHCARD_API_TIMEOUT": ("api", "timeout"),
            "FLASHCARD_MAX_CONCURRENT": ("processing", "max_concurrent"),
            "FLASHCARD_CACHE_ENABLED": ("cache", "enabled"),
            "FLASHCARD_CACHE_PATH": ("cache", "path"),
            "FLASHCARD_DB_PATH": ("database", "path"),
            "FLASHCARD_LOG_LEVEL": ("logging", "level"),
        }
        
        for env_var, (section, field) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                section_obj = getattr(config, section)
                # Convert types as needed
                if field in ["timeout", "max_concurrent", "connection_pool_size"]:
                    value = int(value)
                elif field == "enabled":
                    value = value.lower() in ["true", "1", "yes"]
                elif field in ["path", "file"]:
                    value = Path(value)
                
                setattr(section_obj, field, value)
        
        return config
    
    def merge_with_args(self, **kwargs) -> "Config":
        """Merge configuration with command-line arguments"""
        config_dict = self.dict()
        
        # Map CLI args to config paths
        arg_mappings = {
            "config": None,  # Skip config file arg
            "log_level": ("logging", "level"),
            "no_color": None,  # Handle separately
            "json": None,  # Handle separately
            "quiet": None,  # Handle separately
            "concurrent": ("processing", "max_concurrent"),
            "output": None,  # Handle separately
            "format": ("output", "default_format"),
            "limit": None,  # Handle separately
            "batch_size": ("processing", "batch_size"),
        }
        
        for arg, path in arg_mappings.items():
            if arg in kwargs and kwargs[arg] is not None and path is not None:
                section, field = path
                if section not in config_dict:
                    config_dict[section] = {}
                config_dict[section][field] = kwargs[arg]
        
        return Config(**config_dict)
    
    def save(self, path: Path) -> None:
        """Save configuration to YAML file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(
                self.dict(exclude_unset=True, exclude_defaults=False),
                f,
                default_flow_style=False,
                sort_keys=False
            )
    
    def validate_api_key(self) -> bool:
        """Check if API key is configured"""
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("FLASHCARD_API_KEY")
        return bool(api_key)


def load_config(
    config_file: Optional[Path] = None,
    use_env: bool = True,
    **kwargs
) -> Config:
    """Load configuration with hierarchy: CLI args > ENV > file > defaults"""
    
    # Start with defaults
    if config_file and config_file.exists():
        config = Config.from_file(config_file)
    else:
        config = Config()
    
    # Override with environment variables
    if use_env:
        env_config = Config.from_env()
        config = Config(**{**config.dict(), **env_config.dict(exclude_unset=True)})
    
    # Override with CLI arguments
    if kwargs:
        config = config.merge_with_args(**kwargs)
    
    return config


def init_config(path: Path = Path(".flashcard-config.yml")) -> Path:
    """Initialize a new configuration file with defaults"""
    config = Config()
    config.save(path)
    return path
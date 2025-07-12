"""Phase 1: Configuration System Tests

Tests for configuration loading hierarchy, environment variables,
validation, and error handling.
"""

import pytest
import os
import yaml
from pathlib import Path
import tempfile

from flashcard_pipeline.cli.config import (
    Config,
    ApiConfig,
    ProcessingConfig,
    CacheConfig,
    DatabaseConfig,
    OutputConfig,
    LoggingConfig,
    load_config,
    init_config
)


class TestConfigurationDefaults:
    """Test default configuration values"""
    
    def test_default_config_creation(self):
        """Test creating config with all defaults"""
        config = Config()
        
        # API defaults
        assert config.api.provider == "openrouter"
        assert config.api.model == "anthropic/claude-3.5-sonnet"
        assert config.api.base_url == "https://openrouter.ai/api/v1"
        assert config.api.timeout == 30
        assert config.api.max_retries == 3
        
        # Processing defaults
        assert config.processing.max_concurrent == 20
        assert config.processing.batch_size == 100
        assert config.processing.rate_limit["requests_per_minute"] == 60
        assert config.processing.rate_limit["tokens_per_minute"] == 90000
        
        # Cache defaults
        assert config.cache.enabled == True
        assert config.cache.path == Path(".cache/flashcards")
        assert config.cache.ttl_days == 30
        assert config.cache.max_size_gb == 10.0
        
        # Database defaults
        assert config.database.path == Path("pipeline.db")
        assert config.database.connection_pool_size == 5
        assert config.database.enable_wal == True
        
        # Output defaults
        assert config.output.default_format == "tsv"
        assert config.output.anki["deck_name"] == "Korean Vocabulary"
        assert "korean" in config.output.anki["tags"]
        
        # Logging defaults
        assert config.logging.level == "INFO"
        assert config.logging.file == Path("flashcard-pipeline.log")
        assert config.logging.max_size_mb == 100
        assert config.logging.retention_days == 7
    
    def test_nested_config_access(self):
        """Test accessing nested configuration values"""
        config = Config()
        
        # Test nested dict access
        assert config.output.quality["min_confidence"] == 0.8
        assert config.output.quality["require_examples"] == True
        
        # Test empty plugin config
        assert config.plugins == {}
        assert config.presets == {}


class TestConfigurationLoading:
    """Test loading configuration from files and environment"""
    
    def test_load_from_yaml_file(self, tmp_path):
        """Test loading configuration from YAML file"""
        config_file = tmp_path / "test_config.yml"
        
        config_data = {
            "api": {
                "model": "custom/model",
                "timeout": 60
            },
            "processing": {
                "max_concurrent": 10,
                "batch_size": 50
            },
            "cache": {
                "enabled": False
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config.from_file(config_file)
        
        # Check overridden values
        assert config.api.model == "custom/model"
        assert config.api.timeout == 60
        assert config.processing.max_concurrent == 10
        assert config.processing.batch_size == 50
        assert config.cache.enabled == False
        
        # Check defaults still apply
        assert config.api.provider == "openrouter"
        assert config.database.enable_wal == True
    
    def test_load_from_missing_file(self):
        """Test loading from non-existent file returns defaults"""
        config = Config.from_file(Path("non_existent_config.yml"))
        
        # Should return default config
        assert config.api.provider == "openrouter"
        assert config.processing.max_concurrent == 20
    
    def test_environment_variable_override(self, monkeypatch):
        """Test environment variables override config"""
        # Set environment variables
        monkeypatch.setenv("FLASHCARD_API_MODEL", "env/model")
        monkeypatch.setenv("FLASHCARD_API_TIMEOUT", "120")
        monkeypatch.setenv("FLASHCARD_MAX_CONCURRENT", "5")
        monkeypatch.setenv("FLASHCARD_CACHE_ENABLED", "false")
        monkeypatch.setenv("FLASHCARD_CACHE_PATH", "/tmp/cache")
        monkeypatch.setenv("FLASHCARD_LOG_LEVEL", "DEBUG")
        
        config = Config.from_env()
        
        assert config.api.model == "env/model"
        assert config.api.timeout == 120
        assert config.processing.max_concurrent == 5
        assert config.cache.enabled == False
        assert config.cache.path == Path("/tmp/cache")
        assert config.logging.level == "DEBUG"
    
    def test_config_hierarchy(self, tmp_path, monkeypatch):
        """Test config loading hierarchy: CLI > ENV > file > defaults"""
        # Create config file
        config_file = tmp_path / "config.yml"
        with open(config_file, 'w') as f:
            yaml.dump({
                "api": {"model": "file/model"},
                "processing": {"batch_size": 200}
            }, f)
        
        # Set environment variable
        monkeypatch.setenv("FLASHCARD_API_MODEL", "env/model")
        
        # Load with hierarchy
        config = load_config(
            config_file=config_file,
            use_env=True,
            concurrent=30  # CLI argument
        )
        
        # CLI args should take precedence
        assert config.processing.max_concurrent == 30
        
        # ENV should override file
        assert config.api.model == "env/model"
        
        # File should override defaults
        assert config.processing.batch_size == 200
        
        # Defaults should still apply
        assert config.cache.ttl_days == 30


class TestConfigurationValidation:
    """Test configuration validation rules"""
    
    def test_processing_config_validation(self):
        """Test processing config bounds"""
        # Valid range
        config = ProcessingConfig(max_concurrent=25)
        assert config.max_concurrent == 25
        
        # Test upper bound
        config = ProcessingConfig(max_concurrent=50)
        assert config.max_concurrent == 50
        
        # Test exceeding upper bound
        with pytest.raises(ValueError):
            ProcessingConfig(max_concurrent=51)
        
        # Test lower bound
        with pytest.raises(ValueError):
            ProcessingConfig(max_concurrent=0)
    
    def test_api_key_validation(self, monkeypatch):
        """Test API key validation"""
        # Clear any existing API keys first
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("FLASHCARD_API_KEY", raising=False)
        
        config = Config()
        
        # No API key set
        assert config.validate_api_key() == False
        
        # Set OPENROUTER_API_KEY
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        assert config.validate_api_key() == True
        
        # Clear and set FLASHCARD_API_KEY
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("FLASHCARD_API_KEY", "test-key-2")
        assert config.validate_api_key() == True
    
    def test_path_type_conversion(self):
        """Test Path type conversion from strings"""
        config_dict = {
            "cache": {"path": "/tmp/test"},
            "database": {"path": "test.db"},
            "logging": {"file": "logs/app.log"}
        }
        
        config = Config(**config_dict)
        
        assert isinstance(config.cache.path, Path)
        assert config.cache.path == Path("/tmp/test")
        assert isinstance(config.database.path, Path)
        assert isinstance(config.logging.file, Path)


class TestConfigurationPersistence:
    """Test saving and loading configuration"""
    
    def test_save_config_to_file(self, tmp_path):
        """Test saving configuration to YAML"""
        config = Config()
        config.api.model = "custom/model"
        config.processing.max_concurrent = 15
        
        save_path = tmp_path / "saved_config.yml"
        config.save(save_path)
        
        assert save_path.exists()
        
        # Load and verify
        loaded_config = Config.from_file(save_path)
        assert loaded_config.api.model == "custom/model"
        assert loaded_config.processing.max_concurrent == 15
    
    def test_init_config_creates_file(self, tmp_path):
        """Test init_config creates default config file"""
        config_path = tmp_path / "new_config.yml"
        
        result_path = init_config(config_path)
        
        assert result_path == config_path
        assert config_path.exists()
        
        # Verify it's a valid config
        config = Config.from_file(config_path)
        assert config.api.provider == "openrouter"


class TestConfigurationMerging:
    """Test merging configurations with CLI arguments"""
    
    def test_merge_with_cli_args(self):
        """Test merging config with command-line arguments"""
        config = Config()
        
        merged = config.merge_with_args(
            log_level="DEBUG",
            concurrent=15,
            batch_size=50,
            format="json"
        )
        
        assert merged.logging.level == "DEBUG"
        assert merged.processing.max_concurrent == 15
        assert merged.processing.batch_size == 50
        assert merged.output.default_format == "json"
        
        # Original should be unchanged
        assert config.logging.level == "INFO"
    
    def test_merge_ignores_none_values(self):
        """Test merging ignores None CLI arguments"""
        config = Config()
        config.processing.max_concurrent = 10
        
        merged = config.merge_with_args(
            concurrent=None,
            batch_size=None,
            format=None
        )
        
        # Should keep original values
        assert merged.processing.max_concurrent == 10
        assert merged.processing.batch_size == 100
        assert merged.output.default_format == "tsv"


class TestPluginConfiguration:
    """Test plugin and preset configuration"""
    
    def test_plugin_config_loading(self, tmp_path):
        """Test loading plugin configurations"""
        config_file = tmp_path / "config.yml"
        
        config_data = {
            "plugins": {
                "custom_formatter": {
                    "enabled": True,
                    "options": {
                        "format": "custom",
                        "template": "template.j2"
                    }
                }
            },
            "presets": {
                "beginner": {
                    "difficulty": "easy",
                    "max_examples": 2
                }
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config.from_file(config_file)
        
        assert "custom_formatter" in config.plugins
        assert config.plugins["custom_formatter"]["enabled"] == True
        assert config.plugins["custom_formatter"]["options"]["format"] == "custom"
        
        assert "beginner" in config.presets
        assert config.presets["beginner"]["difficulty"] == "easy"


class TestEnvironmentVariableEdgeCases:
    """Test edge cases in environment variable handling"""
    
    def test_boolean_env_var_parsing(self, monkeypatch):
        """Test parsing boolean values from env vars"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("invalid", False)
        ]
        
        for env_value, expected in test_cases:
            monkeypatch.setenv("FLASHCARD_CACHE_ENABLED", env_value)
            config = Config.from_env()
            assert config.cache.enabled == expected
    
    def test_integer_env_var_parsing(self, monkeypatch):
        """Test parsing integer values from env vars"""
        monkeypatch.setenv("FLASHCARD_API_TIMEOUT", "45")
        monkeypatch.setenv("FLASHCARD_MAX_CONCURRENT", "25")
        
        config = Config.from_env()
        
        assert config.api.timeout == 45
        assert config.processing.max_concurrent == 25
        
        # Test invalid integer
        monkeypatch.setenv("FLASHCARD_API_TIMEOUT", "not_a_number")
        with pytest.raises(ValueError):
            Config.from_env()
    
    def test_path_env_var_parsing(self, monkeypatch):
        """Test parsing path values from env vars"""
        monkeypatch.setenv("FLASHCARD_CACHE_PATH", "/custom/cache/path")
        monkeypatch.setenv("FLASHCARD_DB_PATH", "custom.db")
        
        config = Config.from_env()
        
        assert config.cache.path == Path("/custom/cache/path")
        assert config.database.path == Path("custom.db")
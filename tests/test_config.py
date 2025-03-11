"""
Tests for configuration loading functionality.
"""

import os
import tempfile
import yaml
import pytest
from pathlib import Path

from wikly.config import load_config, DEFAULT_CONFIG_PATH


def test_load_config_default_values():
    """Test that load_config returns default values when no file is present."""
    config = load_config("nonexistent_file.yaml")
    
    # Verify default config values
    assert "wikly" in config
    assert "export" in config
    assert "gemini" in config
    assert config["wikly"]["host"] is None
    assert config["wikly"]["api_key"] is None
    assert config["wikly"]["use_env_vars"] is True
    
    assert config["export"]["default_format"] == "markdown"
    assert config["export"]["default_output"] == "wiki_export"
    assert config["export"]["delay"] == 0.1
    assert config["export"]["metadata_file"] == ".wikly_export_metadata.json"
    assert config["gemini"]["api_key"] is None
    assert config["gemini"]["default_model"] == "gemini-2.0-flash"
    assert config["gemini"]["delay"] == 1.0


def test_load_config_with_file():
    """Test that load_config loads values from a file."""
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        config_content = {
            "wikly": {
                "host": "https://test-wiki.example.com",
                "api_key": "test-api-key",
                "use_env_vars": False
            },
            "export": {
                "default_format": "json",
                "default_output": "test_output",
                "delay": 0.5
            }
        }
        yaml.dump(config_content, temp)
        temp_path = temp.name
    
    try:
        # Load config from temporary file
        config = load_config(temp_path)
        
        # Verify loaded values
        assert config["wikly"]["host"] == "https://test-wiki.example.com"
        assert config["wikly"]["api_key"] == "test-api-key"
        assert config["export"]["default_format"] == "json"
        assert config["export"]["default_output"] == "test_output"
        assert config["export"]["delay"] == 0.5
        assert config["gemini"]["api_key"] is None
        assert config["gemini"]["default_model"] == "gemini-2.0-flash"
        assert config["gemini"]["delay"] == 1.0
    finally:
        os.unlink(temp_path)


def test_load_config_partial_values():
    """Test that load_config merges partial values with defaults."""
    # Create a test config file with only some values
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "partial_config.yaml")
        
        # Create a partial config
        partial_config = {
            "wikly": {
                "host": "https://partial-wiki.example.com"
                # Missing api_key
            },
            "export": {
                "default_format": "html"
                # Missing other export settings
            }
            # Missing gemini section
        }
        
        # Write config to file
        with open(config_path, 'w') as f:
            yaml.dump(partial_config, f)
        
        # Load the config
        config = load_config(config_path)
        
        # Verify specified values are loaded
        assert config["wikly"]["host"] == "https://partial-wiki.example.com"
        assert config["export"]["default_format"] == "html"
        
        # Verify default values are used for missing fields
        assert config["wikly"]["api_key"] is None  # Default
        assert config["wikly"]["use_env_vars"] is True  # Default
        assert "default_output" in config["export"]
        assert "delay" in config["export"]
        assert "metadata_file" in config["export"]
        assert "gemini" in config
        assert "api_key" in config["gemini"]
        assert "default_model" in config["gemini"]
        assert "delay" in config["gemini"] 
"""
Tests for configuration loading functionality.
"""

import os
import tempfile
import yaml
import pytest
from pathlib import Path

from wikijs_exporter.cli import load_config, DEFAULT_CONFIG_PATH


def test_load_config_default_values():
    """Test that load_config returns default values when no file is present."""
    # Test with a non-existent file
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_path = os.path.join(tmpdir, "does_not_exist.yaml")
        config = load_config(non_existent_path)
        
        # Verify default values are returned
        assert "wikijs" in config
        assert "export" in config
        assert "gemini" in config
        assert config["wikijs"]["host"] == ""
        assert config["wikijs"]["api_key"] == ""


def test_load_config_with_file():
    """Test that load_config correctly loads values from a file."""
    # Create a test config file
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "test_config.yaml")
        
        # Create a sample config
        test_config = {
            "wikijs": {
                "host": "https://test-wiki.example.com",
                "api_key": "test-api-key"
            },
            "export": {
                "default_format": "markdown",
                "default_output": "test_output",
                "delay": 0.5,
                "metadata_file": "test_metadata.json"
            },
            "gemini": {
                "api_key": "test-gemini-key"
            }
        }
        
        # Write config to file
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Load the config
        config = load_config(config_path)
        
        # Verify values match
        assert config["wikijs"]["host"] == "https://test-wiki.example.com"
        assert config["wikijs"]["api_key"] == "test-api-key"
        assert config["export"]["default_format"] == "markdown"
        assert config["export"]["default_output"] == "test_output"
        assert config["export"]["delay"] == 0.5
        assert config["export"]["metadata_file"] == "test_metadata.json"
        assert config["gemini"]["api_key"] == "test-gemini-key"


def test_load_config_partial_values():
    """Test that load_config merges partial values with defaults."""
    # Create a test config file with only some values
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "partial_config.yaml")
        
        # Create a partial config
        partial_config = {
            "wikijs": {
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
        assert config["wikijs"]["host"] == "https://partial-wiki.example.com"
        assert config["export"]["default_format"] == "html"
        
        # Verify default values are used for missing fields
        assert config["wikijs"]["api_key"] == ""  # Default
        assert "default_output" in config["export"]
        assert "delay" in config["export"]
        assert "metadata_file" in config["export"]
        assert "gemini" in config
        assert "api_key" in config["gemini"] 
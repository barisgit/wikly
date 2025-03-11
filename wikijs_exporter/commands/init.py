"""
Initialize configuration command for Wiki.js Exporter.
"""

import os
import yaml
import click
from pathlib import Path
import re
from typing import Dict, Any, Optional

from ..config import DEFAULT_CONFIG_PATH, create_sample_style_guide, create_sample_ai_guide

def read_existing_config(path: str) -> Optional[str]:
    """
    Read an existing configuration file, preserving comments and format.
    
    Args:
        path: Path to the configuration file
        
    Returns:
        The raw content of the file, or None if file doesn't exist
    """
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        click.echo(f"Warning: Could not read existing configuration: {e}")
        return None

def parse_yaml_config(content: str) -> Dict[str, Any]:
    """
    Parse YAML configuration content.
    
    Args:
        content: YAML content string
        
    Returns:
        Dictionary of configuration values
    """
    try:
        return yaml.safe_load(content) or {}
    except Exception as e:
        click.echo(f"Warning: Could not parse existing configuration: {e}")
        return {}

def merge_config_with_defaults(existing_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge existing configuration with default values, ensuring all keys exist.
    
    Args:
        existing_config: Existing configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    # Define default configuration structure
    default_config = {
        "wikijs": {
            "host": "https://your-wiki.example.com",
            "api_key": "your_api_token_here",
            "use_env_vars": True
        },
        "export": {
            "default_format": "markdown",
            "default_output": "wiki_export",
            "delay": 0.1,
            "metadata_file": ".wikijs_export_metadata.json"
        },
        "gemini": {
            "api_key": "your_gemini_api_key_here",
            "delay": 1.0,
            "style_guide_file": "wiki_style_guide.md",
            "ai_guide_file": "ai_instructions.md"
        },
        "sitemap": {
            "max_chars": 10000,
            "detail_level": 2,
            "show_by_default": False
        }
    }
    
    # Helper function to recursively merge dictionaries
    def deep_merge(source, destination):
        for key, value in source.items():
            if key in destination:
                if isinstance(value, dict) and isinstance(destination[key], dict):
                    deep_merge(value, destination[key])
            else:
                destination[key] = value
        return destination
    
    # Start with existing config and add missing values
    merged = existing_config.copy()
    for section, settings in default_config.items():
        if section not in merged:
            merged[section] = {}
        
        if isinstance(settings, dict):
            for key, value in settings.items():
                if section in merged and key not in merged[section]:
                    merged[section][key] = value
    
    return merged

def generate_config_content(config: Dict[str, Any]) -> str:
    """
    Generate YAML configuration content with helpful comments.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        YAML configuration string with comments
    """
    # Top comment
    content = """# Configuration for Wiki.js Exporter

"""
    
    # Section comments
    section_comments = {
        "wikijs": """# Wiki.js instance settings
""",
        "export": """
# Export settings
""",
        "gemini": """
# Gemini AI settings for content analysis
""",
        "sitemap": """
# Sitemap generation settings
"""
    }
    
    # Field-specific comments
    field_comments = {
        "wikijs": {
            "host": "  # Wiki.js host URL (e.g., https://wiki.example.com)",
            "api_key": "  # API token with read permissions (from Wiki.js Admin > API Access)",
            "use_env_vars": "  # Whether to fall back to environment variables if values aren't specified"
        },
        "export": {
            "default_format": "  # Default export format (json, markdown, or html)",
            "default_output": "  # Default output directory or file",
            "delay": "  # Delay between API requests in seconds",
            "metadata_file": "  # File to store export metadata"
        },
        "gemini": {
            "api_key": "  # Google Gemini API key",
            "delay": "  # Delay between API calls in seconds",
            "style_guide_file": "  # Path to style guide file",
            "ai_guide_file": "  # Path to AI-specific instructions file"
        },
        "sitemap": {
            "max_chars": "  # Maximum characters to include in the sitemap",
            "detail_level": "  # Level of detail (0=basic structure, 1=with metadata, 2=with descriptions, 3=with outlines)",
            "show_by_default": "  # Whether to show sitemap by default in commands that support it"
        }
    }
    
    # Generate YAML content with comments
    for section, values in config.items():
        if section in section_comments:
            content += section_comments[section]
        
        content += f"{section}:\n"
        
        for key, value in values.items():
            # Format the value properly for YAML
            if value is None:
                yaml_value = "null"
            elif isinstance(value, bool):
                yaml_value = str(value).lower()
            elif isinstance(value, (int, float)):
                yaml_value = str(value)
            else:
                yaml_value = f"{value}"
            
            # Add comment if available
            comment = field_comments.get(section, {}).get(key, "")
            content += f"  {key}: {yaml_value}{comment}\n"
        
    return content

@click.command('init')
@click.option('--path', default=DEFAULT_CONFIG_PATH, help=f'Path to create configuration file (default: {DEFAULT_CONFIG_PATH})')
@click.option('--force/--no-force', default=False, help='Force overwrite of existing files')
def init_config(path: str, force: bool):
    """Initialize a new configuration file with sample settings and create supporting files."""
    config_path = Path(path)
    
    # Define paths for additional files
    style_guide_path = "wiki_style_guide.md"
    ai_guide_path = "ai_instructions.md"
    
    # Check if file already exists and read it
    existing_content = None
    existing_config = {}
    
    if config_path.exists() and not force:
        click.echo(f"Configuration file {path} exists, checking for missing settings...")
        existing_content = read_existing_config(path)
        if existing_content:
            existing_config = parse_yaml_config(existing_content)
    
    # Merge with defaults to add any missing settings
    merged_config = merge_config_with_defaults(existing_config)
    
    # Ensure paths to supporting files are correct
    merged_config["gemini"]["style_guide_file"] = style_guide_path
    merged_config["gemini"]["ai_guide_file"] = ai_guide_path
    
    # Make sure sitemap section exists
    if "sitemap" not in merged_config:
        merged_config["sitemap"] = {}
        
    # Set default sitemap values if not present
    for key, value in {"max_chars": 10000, "detail_level": 2, "show_by_default": False}.items():
        if key not in merged_config["sitemap"]:
            merged_config["sitemap"][key] = value
    
    # Generate new config content
    new_config_content = generate_config_content(merged_config)
    
    # Write the updated configuration file
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_config_content)
        
        if existing_content:
            click.echo(f"✓ Configuration file updated with missing settings at {path}")
        else:
            click.echo(f"✓ Configuration file created at {path}")
    except Exception as e:
        click.echo(f"Error creating configuration file: {str(e)}")
        return
    
    # Create sample style guide file if it doesn't exist or force is True
    if not os.path.exists(style_guide_path) or force:
        try:
            with open(style_guide_path, 'w') as f:
                f.write(create_sample_style_guide())
            click.echo(f"✓ Sample style guide created at {style_guide_path}")
        except Exception as e:
            click.echo(f"Error creating style guide file: {str(e)}")
    else:
        click.echo(f"Style guide file {style_guide_path} already exists. Use --force to overwrite.")
    
    # Create sample AI instructions file if it doesn't exist or force is True
    if not os.path.exists(ai_guide_path) or force:
        try:
            with open(ai_guide_path, 'w') as f:
                f.write(create_sample_ai_guide())
            click.echo(f"✓ Sample AI instructions created at {ai_guide_path}")
        except Exception as e:
            click.echo(f"Error creating AI instructions file: {str(e)}")
    else:
        click.echo(f"AI instructions file {ai_guide_path} already exists. Use --force to overwrite.")
    
    click.echo("\nConfiguration setup complete!")
    click.echo("Edit these files to configure your Wiki.js exporter:")
    click.echo(f"1. {path} - Main configuration")
    click.echo(f"2. {style_guide_path} - Style guidelines for content")
    click.echo(f"3. {ai_guide_path} - AI-specific analysis instructions") 
"""
Initialize configuration command for Wiki.js Exporter.
"""

import os
import click
from pathlib import Path

from ..config import DEFAULT_CONFIG_PATH, create_sample_style_guide, create_sample_ai_guide

@click.command('init')
@click.option('--path', default=DEFAULT_CONFIG_PATH, help=f'Path to create configuration file (default: {DEFAULT_CONFIG_PATH})')
@click.option('--force/--no-force', default=False, help='Force overwrite of existing files')
def init_config(path: str, force: bool):
    """Initialize a new configuration file with sample settings and create supporting files."""
    config_path = Path(path)
    
    # Check if file already exists
    if config_path.exists() and not force:
        click.echo(f"Configuration file {path} already exists. Use --force to overwrite.")
        return
    
    # Define paths for additional files
    style_guide_path = "wiki_style_guide.md"
    ai_guide_path = "ai_instructions.md"
    
    # Sample configuration as YAML string with comments
    sample_config_yaml = """# Configuration for Wiki.js Exporter

wikijs:
  # Wiki.js host URL (e.g., https://wiki.example.com)
  host: https://your-wiki.example.com
  # API token with read permissions (from Wiki.js Admin > API Access)
  api_key: your_api_token_here
  # Whether to fall back to environment variables if values aren't specified
  use_env_vars: true

export:
  # Default export format (json, markdown, or html)
  default_format: markdown
  # Default output directory or file
  default_output: wiki_export
  # Delay between API requests in seconds
  delay: 0.1
  # File to store export metadata
  metadata_file: .wikijs_export_metadata.json

gemini:
  # Google Gemini API key
  api_key: your_gemini_api_key_here
  # Default Gemini model to use
  default_model: gemini-2.0-flash
  # Delay between API calls in seconds
  delay: 1.0
  # Path to style guide file
  style_guide_file: {style_guide}
  # Path to AI-specific instructions file
  ai_guide_file: {ai_guide}
""".format(style_guide=style_guide_path, ai_guide=ai_guide_path)
    
    # Write the configuration file
    try:
        with open(path, 'w') as f:
            f.write(sample_config_yaml)
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
    
    click.echo("Edit these files to configure your Wiki.js exporter:")
    click.echo(f"1. {path} - Main configuration")
    click.echo(f"2. {style_guide_path} - Style guidelines for content")
    click.echo(f"3. {ai_guide_path} - AI-specific analysis instructions") 
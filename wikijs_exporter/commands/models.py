"""
Gemini model listing command for Wiki.js Exporter.
"""

import click
from typing import Optional

from ..config import DEFAULT_CONFIG_PATH, load_config
from ..utils import load_env_variables
from ..gemini import GeminiAnalyzer

@click.command('list-models')
@click.option('--api-key', help='Google Gemini API key')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
def list_gemini_models(api_key: Optional[str], config_file: Optional[str], debug: bool):
    """List available Gemini models for content analysis."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    gemini_api_key = api_key or config["gemini"]["api_key"] or env_gemini_key
    
    if not gemini_api_key:
        click.echo("Error: Gemini API key is required. Provide it using --api-key, config file, or set GEMINI_API_KEY in .env file.")
        return
    
    if debug:
        click.echo(f"Debug: Using Gemini API key: {gemini_api_key[:4]}...{gemini_api_key[-4:]}")
    
    # Create the analyzer
    analyzer = GeminiAnalyzer(api_key=gemini_api_key, debug=debug)
    
    click.echo("Fetching available Gemini models...")
    models = analyzer.list_available_models()
    
    if not models:
        click.echo("No Gemini models found or error retrieving models.")
        return
    
    click.echo("\nAvailable Gemini models:")
    for model in models:
        click.echo(f"- {model}") 
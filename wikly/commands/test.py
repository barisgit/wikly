"""
Test connection command for Wiki.js Exporter.
"""

import click
from typing import Optional

from ..config import DEFAULT_CONFIG_PATH, load_config
from ..utils import load_env_variables
from ..api import WikilyAPI

@click.command('test')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def test_connection(url: Optional[str], token: Optional[str], debug: bool, config_file: Optional[str]):
    """Test connection to the Wiki.js GraphQL API."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    api_token = token or config["wikly"]["api_key"] or env_token
    base_url = url or config["wikly"]["host"] or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url, config file, or set WIKLY_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token, config file, or set WIKLY_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikilyAPI(base_url, api_token, debug)
    
    # Test connection
    success = api.test_connection()
    
    if success:
        click.echo("✓ Connection test successful")
    else:
        click.echo("✗ Connection test failed") 
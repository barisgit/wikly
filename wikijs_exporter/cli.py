"""
Command-line interface for Wiki.js Exporter.
"""

import click
import os
from typing import Optional

from .api import WikiJSAPI
from .utils import load_env_variables, save_pages_to_file, save_pages_to_markdown, save_pages_to_html

@click.group()
@click.version_option()
def cli():
    """Wiki.js Exporter - Export content from a Wiki.js instance."""
    pass

@cli.command('test')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
def test_connection(url: Optional[str], token: Optional[str], debug: bool):
    """Test connection to the Wiki.js GraphQL API."""
    # Load environment variables if not provided as options
    env_token, env_url = load_env_variables()
    
    # Use CLI options if provided, fall back to environment variables
    api_token = token or env_token
    base_url = url or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token or set WIKIJS_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikiJSAPI(base_url, api_token, debug)
    
    # Test connection
    if api.test_connection():
        click.echo("✓ Connection successful")
    else:
        click.echo("✗ Connection failed")

@cli.command('list')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--output', default='wiki_pages.json', help='Output file (default: wiki_pages.json)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
def list_pages(url: Optional[str], token: Optional[str], output: str, debug: bool):
    """Fetch a list of all pages (metadata only) from Wiki.js."""
    # Load environment variables if not provided as options
    env_token, env_url = load_env_variables()
    
    # Use CLI options if provided, fall back to environment variables
    api_token = token or env_token
    base_url = url or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token or set WIKIJS_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikiJSAPI(base_url, api_token, debug)
    
    # Fetch pages
    pages = api.fetch_pages()
    
    if pages:
        # Save pages to file
        save_pages_to_file(pages, output)
    else:
        click.echo("No pages found or error occurred.")

@cli.command('export')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--output', default='wiki_pages_with_content.json', help='Output file (default: wiki_pages_with_content.json)')
@click.option('--delay', type=float, default=0.1, help='Delay in seconds between requests (default: 0.1)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.option('--format', type=click.Choice(['json', 'markdown', 'html']), default='json', 
              help='Output format (json, markdown, or html)')
def export_pages(url: Optional[str], token: Optional[str], output: str, delay: float, debug: bool, format: str):
    """Fetch all pages with their content from Wiki.js."""
    # Load environment variables if not provided as options
    env_token, env_url = load_env_variables()
    
    # Use CLI options if provided, fall back to environment variables
    api_token = token or env_token
    base_url = url or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token or set WIKIJS_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikiJSAPI(base_url, api_token, debug)
    
    # Fetch pages with content
    pages = api.fetch_all_pages_with_content(delay)
    
    if not pages:
        click.echo("No pages found or error occurred.")
        return
    
    # Export in the chosen format
    if format == 'json':
        save_pages_to_file(pages, output)
    elif format == 'markdown':
        # If output is a file, use it as a directory name instead
        output_dir = output if os.path.isdir(output) else os.path.splitext(output)[0]
        save_pages_to_markdown(pages, output_dir)
    elif format == 'html':
        # If output is a file, use it as a directory name instead
        output_dir = output if os.path.isdir(output) else os.path.splitext(output)[0]
        save_pages_to_html(pages, output_dir)

if __name__ == '__main__':
    cli() 
"""
Export pages command for Wiki.js Exporter.
"""

import os
import click
from typing import Optional

from ..config import DEFAULT_CONFIG_PATH, load_config
from ..utils import (
    generate_sitemap,
    load_env_variables, 
    save_pages_to_file, 
    save_pages_to_markdown, 
    save_pages_to_html,
    ExportMetadata
)
from ..api import WikilyAPI

@click.command('export')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--output', help='Output file or directory (default: based on format from config)')
@click.option('--delay', type=float, help='Delay in seconds between requests (default: from config)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.option('--format', type=click.Choice(['json', 'markdown', 'html']), help='Output format (json, markdown, or html)')
@click.option('--incremental/--full', default=True, help='Only export pages that have changed since last export (default: incremental)')
@click.option('--force-full', is_flag=True, help='Force full export instead of incremental')
@click.option('--reset-hashes', is_flag=True, help='Reset all content hashes in metadata (forces recomputing all hashes)')
@click.option('--metadata-file', help='File to store export metadata (default: from config)')
@click.option('--show-sitemap/--no-sitemap', default=None, help='Show generated sitemap after export')
@click.option('--sitemap-chars', type=int, help='Max characters for sitemap')
@click.option('--sitemap-detail', type=int, help='Detail level for sitemap (0-3)')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def export_pages(url: Optional[str], token: Optional[str], output: Optional[str], delay: Optional[float], debug: bool, 
                format: Optional[str], incremental: bool, force_full: bool, reset_hashes: bool, 
                metadata_file: Optional[str], show_sitemap: Optional[bool], sitemap_chars: Optional[int], sitemap_detail: Optional[int],
                config_file: Optional[str]):
    """Fetch pages with their content from Wiki.js."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    api_token = token or config["wikly"]["api_key"] or env_token
    base_url = url or config["wikly"]["host"] or env_url
    
    # Load sitemap settings from config
    config_sitemap = config.get("sitemap", {})
    sitemap_max_chars = sitemap_chars or config_sitemap.get("max_chars", 10000)
    sitemap_detail_level = sitemap_detail or config_sitemap.get("detail_level", 2)
    
    # For show_sitemap, None means use config default
    if show_sitemap is None:
        show_sitemap = config_sitemap.get("show_by_default", False)
    
    if debug:
        click.echo(f"Sitemap settings - Show: {show_sitemap}, Max chars: {sitemap_max_chars}, Detail level: {sitemap_detail_level}")
    
    # Get export config values with precedence
    export_format = format or config["export"]["default_format"]
    export_output = output or (
        config["export"]["default_output"] + 
        ("" if export_format == "json" else "_" + export_format)
    )
    export_delay = delay if delay is not None else config["export"]["delay"]
    export_metadata = metadata_file or config["export"]["metadata_file"]
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url, config file, or set WIKLY_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token, config file, or set WIKLY_API_KEY in .env file.")
        return
    
    # Force full export overrides incremental flag
    if force_full:
        incremental = False
    
    if debug:
        click.echo("Debug mode enabled")
        if incremental:
            click.echo("Incremental export mode enabled")
        else:
            click.echo("Full export mode enabled")
        if reset_hashes:
            click.echo("Resetting all content hashes")
        click.echo(f"Using format: {export_format}")
        click.echo(f"Output: {export_output}")
        click.echo(f"API delay: {export_delay}s")
    
    # Create API client
    api = WikilyAPI(base_url, api_token, debug)
    
    # Initialize export metadata manager
    metadata = ExportMetadata(export_metadata, debug=debug)
    
    # Reset hashes if requested
    if reset_hashes:
        metadata.reset_hashes()
        
    last_export = metadata.get_last_export_time()
    
    if last_export and incremental:
        click.echo(f"Last export: {last_export}")
    
    # Fetch all pages (metadata only)
    all_pages = api.fetch_pages()
    
    if not all_pages:
        click.echo("No pages found or error occurred.")
        return
    
    # Determine output directory based on format
    output_dir = None
    if export_format != 'json':
        output_dir = export_output if os.path.isdir(export_output) else os.path.splitext(export_output)[0]
    
    if incremental and last_export:
        # Identify pages that need content updates
        outdated_pages = metadata.get_outdated_pages(all_pages, output_dir=output_dir)
        click.echo(f"Found {len(outdated_pages)} pages that need updating (out of {len(all_pages)} total pages)")
        
        # Fetch content only for outdated pages
        pages = api.fetch_pages_with_content_incremental(outdated_pages, all_pages, export_delay)
    else:
        # Perform a full export
        click.echo("Performing full export...")
        pages = api.fetch_all_pages_with_content(export_delay)
    
    if not pages:
        click.echo("No pages exported or error occurred.")
        return
    
    # Save export metadata
    metadata.save_metadata(pages)
    
    # Export in the chosen format
    if export_format == 'json':
        save_pages_to_file(pages, export_output)
        click.echo(f"✓ Exported {len(pages)} pages to {export_output}")
    elif export_format == 'markdown':
        # If output is a file, use it as a directory name instead
        output_dir = export_output if os.path.isdir(export_output) else os.path.splitext(export_output)[0]
        save_pages_to_markdown(pages, output_dir)
        click.echo(f"✓ Exported {len(pages)} pages to {output_dir} in Markdown format")
    elif export_format == 'html':
        # If output is a file, use it as a directory name instead
        output_dir = export_output if os.path.isdir(export_output) else os.path.splitext(export_output)[0]
        save_pages_to_html(pages, output_dir)
        click.echo(f"✓ Exported {len(pages)} pages to {output_dir} in HTML format")

    if show_sitemap and pages:
        click.echo("\nGenerated Wiki Sitemap:")
        click.echo("------------------------")
        sitemap = generate_sitemap(pages, max_chars=sitemap_max_chars, detail_level=sitemap_detail_level)
        click.echo(sitemap)
        click.echo("------------------------\n") 
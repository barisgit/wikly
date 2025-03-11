"""
Command-line interface for Wiki.js Exporter.
"""

import click
import os
from typing import Optional

from .api import WikiJSAPI
from .utils import load_env_variables, save_pages_to_file, save_pages_to_markdown, save_pages_to_html
from .gemini import GeminiAnalyzer

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
    env_url, env_token, env_gemini_key = load_env_variables()
    
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
    env_url, env_token, env_gemini_key = load_env_variables()
    
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
    env_url, env_token, env_gemini_key = load_env_variables()
    
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

@cli.command('analyze')
@click.argument('content_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('style_guide_path', type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--output', default='analysis_results.json', help='Output file for raw results (default: analysis_results.json)')
@click.option('--report', default='analysis_report.html', help='Output file for HTML report (default: analysis_report.html)')
@click.option('--gemini-key', help='Gemini API key (overrides environment variable)')
@click.option('--model', default='gemini-2.0-flash', help='Gemini model to use (default: gemini-1.5-flash)')
@click.option('--delay', type=float, default=1.0, help='Delay in seconds between API calls (default: 1.0)')
@click.option('--ai-guide', type=click.Path(exists=True, file_okay=True, dir_okay=False), help='Optional AI-specific guidance file')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
def analyze_content(content_dir: str, style_guide_path: str, output: str, report: str, 
                    gemini_key: Optional[str], model: str, delay: float, ai_guide: Optional[str], debug: bool):
    """
    Analyze wiki content against a style guide using Gemini AI.
    
    CONTENT_DIR is the directory containing wiki content files (.md or .html)
    STYLE_GUIDE_PATH is the path to a file containing the style guide rules
    
    An optional AI-specific guide file can be provided using --ai-guide to give
    additional instructions to the AI analyzer without changing the human-focused style guide.
    """
    _, _, env_gemini_key = load_env_variables()
    
    api_key = gemini_key or env_gemini_key
    
    if not api_key:
        click.echo("Error: Gemini API key not provided. Please set GEMINI_API_KEY in .env file or use --gemini-key option.")
        return
    
    if debug:
        click.echo(f"Debug: Using Gemini API key: {api_key[:4]}...{api_key[-4:]}")
        click.echo(f"Debug: Using model: {model}")
        click.echo(f"Debug: Content directory: {content_dir}")
        if ai_guide:
            click.echo(f"Debug: Using AI guide file: {ai_guide}")
    
    # Create the analyzer
    analyzer = GeminiAnalyzer(api_key=api_key, debug=debug)
    
    # Set the model to use
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    if model != "gemini-1.5-flash":
        analyzer.api_url = api_url
        if debug:
            click.echo(f"Debug: Set custom model URL: {api_url}")
    
    # Check if style guide exists
    if not os.path.exists(style_guide_path):
        click.echo(f"Error: Style guide file not found: {style_guide_path}")
        return
    
    # Check if content directory exists
    if not os.path.exists(content_dir):
        click.echo(f"Error: Content directory not found: {content_dir}")
        return
    
    click.echo(f"Starting analysis of wiki content in {content_dir}...")
    click.echo(f"Using style guide: {style_guide_path}")
    if ai_guide:
        click.echo(f"Using AI guide: {ai_guide}")
    click.echo(f"Analysis results will be saved to: {output}")
    click.echo(f"HTML report will be saved to: {report}")
    
    # Run the analysis
    results = analyzer.analyze_files(
        content_dir=content_dir,
        style_guide_path=style_guide_path,
        output_file=output,
        delay=delay,
        ai_guide_path=ai_guide
    )
    
    # Create readable report
    click.echo("Creating HTML report...")
    analyzer.create_readable_report(results, report)
    
    click.echo(f"Analysis complete! Processed {len(results)} files.")
    click.echo(f"Results saved to: {output}")
    click.echo(f"HTML report saved to: {report}")
    
    # Count issues
    files_with_issues = sum(1 for r in results if r.get("analysis", {}).get("success", False) and 
                           len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) > 0)
    total_issues = sum(len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) 
                      for r in results if r.get("analysis", {}).get("success", False))
    
    click.echo(f"Found {total_issues} issues in {files_with_issues} files.")
    click.echo(f"Open {report} in your browser to view the detailed report.")

@cli.command('list-models')
@click.option('--gemini-key', help='Gemini API key (overrides environment variable)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
def list_gemini_models(gemini_key: Optional[str], debug: bool):
    """List available Gemini models for content analysis."""
    _, _, env_gemini_key = load_env_variables()
    
    api_key = gemini_key or env_gemini_key
    
    if not api_key:
        click.echo("Error: Gemini API key not provided. Please set GEMINI_API_KEY in .env file or use --gemini-key option.")
        return
    
    if debug:
        click.echo(f"Debug: Using Gemini API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Create the analyzer
    analyzer = GeminiAnalyzer(api_key=api_key, debug=debug)
    
    click.echo("Fetching available Gemini models...")
    models = analyzer.list_available_models()
    
    if not models:
        click.echo("No Gemini models found or error retrieving models.")
        return
    
    click.echo("\nAvailable Gemini Models:")
    click.echo("-" * 80)
    
    for model in models:
        name = model.get('name', '').split('/')[-1]
        display_name = model.get('displayName', 'Unknown')
        description = model.get('description', 'No description')
        version = model.get('version', 'Unknown')
        
        click.echo(f"• {name}")
        click.echo(f"  Display Name: {display_name}")
        click.echo(f"  Version: {version}")
        click.echo(f"  Description: {description}")
        click.echo("")
    
    click.echo("-" * 80)
    click.echo(f"Total models available: {len(models)}")
    click.echo("\nTo use a specific model, update the GeminiAnalyzer.api_url in wikijs_exporter/gemini.py")

if __name__ == '__main__':
    cli() 
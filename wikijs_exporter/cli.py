"""
Command-line interface for Wiki.js Exporter.
"""

import click
import os
import yaml  # Add PyYAML dependency
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import markdown

from .api import WikiJSAPI
from .utils import (
    load_env_variables,
    save_pages_to_file,
    save_pages_to_markdown,
    save_pages_to_html,
    load_pages_from_file,
    load_pages_from_markdown,
    normalize_content,
    calculate_content_hash,
    extract_content_from_file,
    ExportMetadata
)
from .gemini import GeminiAnalyzer
from .analyzer import ContentAnalyzer

# Default config file path
DEFAULT_CONFIG_PATH = "wikijs_config.yaml"

@click.group()
@click.version_option()
def cli():
    """Wiki.js Exporter - Export content from a Wiki.js instance."""
    pass

@cli.command('init')
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

def create_sample_style_guide():
    """Create a sample style guide for wiki content."""
    return """# Wiki Content Style Guide

## General Guidelines
- Use consistent terminology throughout all pages
- Use title case for headings
- Use sentence case for all other text
- Tables should have clear headers and consistent formatting
- Code blocks should be properly formatted with language specified
- Use numbered lists for sequential steps
- Use bullet points for non-sequential items
- Keep paragraphs concise and focused
- Include a clear introduction at the beginning of each page
- Provide a conclusion or summary where appropriate

## Markdown Formatting
- Use the appropriate heading levels (# for main title, ## for sections)
- Use *italics* for emphasis, not all caps
- Use **bold** for important terms or warnings
- Use `code` for inline code references
- Use code blocks with language specifier for multi-line code

## Technical Content
- Define acronyms on first use
- Link to related pages when referencing other topics
- Include examples where helpful
- Tables should be used to present structured data
- Images should have clear captions
- Diagrams should be properly labeled
- Procedures should be numbered and have a clear goal stated

## Language and Tone
- Use active voice where possible
- Be concise and direct
- Avoid jargon unless necessary for the topic
- Maintain professional tone
- Use present tense where possible
- Use second person ("you") when addressing the reader
"""

def create_sample_ai_guide():
    """Create sample AI-specific instructions for content analysis."""
    return """# AI-Specific Analysis Instructions

These instructions are intended for the AI analyzer only and supplement the main style guide.

## Analysis Context
When analyzing wiki content, consider the following additional factors:

1. **Technical Accuracy**: While you cannot verify factual accuracy of domain-specific content, flag statements that appear logically inconsistent or potentially misleading.

2. **Audience Appropriateness**: Our wiki content is intended for technical users with varying levels of expertise. Content should avoid assuming too much prior knowledge but should also not over-explain basic concepts.

3. **Consistency Across Pages**: Flag terminology or formatting that differs significantly from typical patterns in technical documentation.

## Analysis Priorities

Please prioritize issues in this order:
1. Structural problems that affect readability (missing sections, poor organization)
2. Technical clarity issues (ambiguous instructions, unclear explanations)
3. Style and formatting inconsistencies
4. Language and grammar issues

## Response Format

When identifying issues:
- Provide specific, actionable suggestions for improvement
- Consider the context of technical documentation when making recommendations
- Provide severity ratings (high, medium, low) based on how much the issue impacts reader understanding

## Content Types

Our wiki contains several types of content, each with specific requirements:

1. **Tutorials**: Should have clear, sequential steps with expected outcomes stated.
2. **Reference Pages**: Should be comprehensive and well-organized with consistent formatting.
3. **Concept Explanations**: Should build understanding progressively and provide examples.
4. **Troubleshooting Guides**: Should clearly describe problems and solutions with debugging steps.

Please consider the content type when analyzing for style compliance.
"""

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with configuration values
    """
    default_config = {
        "wikijs": {
            "host": None,
            "api_key": None,
            "use_env_vars": True,
        },
        "export": {
            "default_format": "json",
            "default_output": "wiki_export",
            "delay": 0.1,
            "metadata_file": ".wikijs_export_metadata.json"
        },
        "gemini": {
            "api_key": None,
            "default_model": "gemini-1.5-flash",
            "delay": 1.0
        }
    }
    
    if not config_path:
        config_path = DEFAULT_CONFIG_PATH
    
    # Try to load the configuration file
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                click.echo(f"✓ Loaded configuration from {config_path}")
                # Merge with default config
                for section in default_config:
                    if section not in config:
                        config[section] = default_config[section]
                    else:
                        for key in default_config[section]:
                            if key not in config[section]:
                                config[section][key] = default_config[section][key]
                return config
    except Exception as e:
        click.echo(f"Warning: Error loading configuration file: {str(e)}")
    
    # Return default configuration if loading fails
    return default_config

@cli.command('test')
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
    api_token = token or config["wikijs"]["api_key"] or env_token
    base_url = url or config["wikijs"]["host"] or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url, config file, or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token, config file, or set WIKIJS_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikiJSAPI(base_url, api_token, debug)
    
    # Test connection
    success = api.test_connection()
    
    if success:
        click.echo("✓ Connection test successful")
    else:
        click.echo("✗ Connection test failed")

@cli.command('list')
@click.option('--url', help='Base URL of your Wiki.js instance')
@click.option('--token', help='API token with appropriate permissions')
@click.option('--output', default='wiki_pages.json', help='Output file (default: wiki_pages.json)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def list_pages(url: Optional[str], token: Optional[str], output: str, debug: bool, config_file: Optional[str]):
    """Fetch a list of all pages from Wiki.js (without content)."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    api_token = token or config["wikijs"]["api_key"] or env_token
    base_url = url or config["wikijs"]["host"] or env_url
    
    # Check if required parameters are available
    if not base_url:
        click.echo("Error: Wiki.js URL is required. Provide it using --url, config file, or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token, config file, or set WIKIJS_API_KEY in .env file.")
        return
    
    if debug:
        click.echo("Debug mode enabled")
    
    # Create API client
    api = WikiJSAPI(base_url, api_token, debug)
    
    # Fetch pages
    pages = api.fetch_pages()
    
    if not pages:
        click.echo("No pages found or error occurred.")
        return
    
    # Save to file
    save_pages_to_file(pages, output)

@cli.command('export')
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
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def export_pages(url: Optional[str], token: Optional[str], output: Optional[str], delay: Optional[float], debug: bool, 
                format: Optional[str], incremental: bool, force_full: bool, reset_hashes: bool, 
                metadata_file: Optional[str], config_file: Optional[str]):
    """Fetch pages with their content from Wiki.js."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    api_token = token or config["wikijs"]["api_key"] or env_token
    base_url = url or config["wikijs"]["host"] or env_url
    
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
        click.echo("Error: Wiki.js URL is required. Provide it using --url, config file, or set WIKIJS_HOST in .env file.")
        return
    
    if not api_token:
        click.echo("Error: API token is required. Provide it using --token, config file, or set WIKIJS_API_KEY in .env file.")
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
    api = WikiJSAPI(base_url, api_token, debug)
    
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
    elif export_format == 'markdown':
        # If output is a file, use it as a directory name instead
        output_dir = export_output if os.path.isdir(export_output) else os.path.splitext(export_output)[0]
        save_pages_to_markdown(pages, output_dir)
    elif export_format == 'html':
        # If output is a file, use it as a directory name instead
        output_dir = export_output if os.path.isdir(export_output) else os.path.splitext(export_output)[0]
        save_pages_to_html(pages, output_dir)

@cli.command('analyze')
@click.option('--format', type=click.Choice(['json', 'markdown']), default='markdown', 
              help='Format of the input (json or markdown)')
@click.option('--output', help='Output JSON file path (default: analysis_results.json)')
@click.option('--report', help='Output HTML report path (default: analysis_report.html)')
@click.option('--input', help='Input file or directory path (for json or markdown)')
@click.option('--api-key', help='Google Gemini API key')
@click.option('--style-guide', help='Path to style guide file')
@click.option('--ai-guide', help='Path to AI-specific instructions file')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def analyze_content(format: str, output: Optional[str], report: Optional[str], input: Optional[str], 
                   api_key: Optional[str], style_guide: Optional[str], ai_guide: Optional[str], 
                   config_file: Optional[str]):
    """Analyze exported wiki content for style guide compliance."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    if config_file:
        click.echo(f"✓ Loaded configuration from {config_file}")
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    gemini_api_key = api_key or config["gemini"]["api_key"] or env_gemini_key
    style_guide_file = style_guide or config["gemini"].get("style_guide_file", "wiki_style_guide.md")
    ai_guide_file = ai_guide or config["gemini"].get("ai_guide_file", "ai_instructions.md")
    
    # Get export directory from config
    export_format = format or config["export"].get("default_format", "markdown")
    export_output = config["export"].get("default_output", "wiki_export")
    
    # Determine default input path based on format and config
    default_input = None
    if format == 'json':
        default_input = f"{export_output}.json" if export_output else "wiki_pages_with_content.json"
    elif format == 'markdown':
        # If export format is markdown, the directory will be the export output
        if export_output:
            if os.path.isdir(export_output):
                default_input = export_output
            else:
                default_input = f"{export_output}_{format}"
        else:
            default_input = "wiki_pages"
    
    if not gemini_api_key:
        click.echo("Error: Gemini API key is required. Provide it using --api-key, config file, or set GEMINI_API_KEY in .env file.")
        return
    
    # Set defaults or use provided values for other parameters
    output_file = output or "analysis_results.json"
    report_file = report or "analysis_report.html"
    
    # Check if style guide file exists
    if not os.path.exists(style_guide_file):
        click.echo(f"Warning: Style guide file not found at {style_guide_file}. Using default style guide.")
        style_guide_content = create_sample_style_guide()
    else:
        try:
            with open(style_guide_file, 'r') as f:
                style_guide_content = f.read()
            click.echo(f"Using style guide from {style_guide_file}")
        except Exception as e:
            click.echo(f"Error reading style guide file: {str(e)}")
            return
    
    # Check if AI guide file exists
    ai_guide_content = None
    if os.path.exists(ai_guide_file):
        try:
            with open(ai_guide_file, 'r') as f:
                ai_guide_content = f.read()
            click.echo(f"Using AI instructions from {ai_guide_file}")
        except Exception as e:
            click.echo(f"Warning: Could not read AI instructions file: {str(e)}")
    else:
        click.echo(f"Note: AI instructions file not found at {ai_guide_file}. Using only the style guide.")
    
    # Determine input source based on format
    input_source = input or default_input
    
    if format == 'json':
        if not os.path.exists(input_source):
            click.echo(f"Error: Input file {input_source} not found.")
            return
        data = load_pages_from_file(input_source)
    elif format == 'markdown':
        if not os.path.exists(input_source):
            click.echo(f"Error: Input directory {input_source} not found.")
            return
        data = load_pages_from_markdown(input_source)
    
    if not data:
        click.echo("Error: No content loaded for analysis.")
        return
    
    # Analyze content
    click.echo(f"Analyzing {len(data)} pages from {input_source}...")
    analyzer = ContentAnalyzer(gemini_api_key, debug=True)
    results = analyzer.analyze_pages(data, style_guide_content, ai_guide_content)
    
    # Save JSON results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    click.echo(f"Analysis complete. JSON results saved to {output_file}")
    
    # Generate HTML report
    try:
        create_html_report(results, report_file, style_guide_content)
        click.echo(f"HTML report saved to {report_file}")
    except Exception as e:
        click.echo(f"Error creating HTML report: {str(e)}")
    
    # Report summary
    files_with_issues = sum(1 for r in results if r.get("analysis", {}).get("success", False) and 
                           len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) > 0)
    total_issues = sum(len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) 
                      for r in results if r.get("analysis", {}).get("success", False))
    
    click.echo(f"Found {total_issues} issues in {files_with_issues} files.")
    click.echo(f"Open {report_file} in your browser to view the detailed report.")

def create_html_report(results: List[Dict[str, Any]], output_file: str, style_guide: str = None) -> None:
    """
    Create an HTML report from analysis results.
    
    Args:
        results: Analysis results
        output_file: Output file path
        style_guide: Style guide content (optional)
    """
    try:
        # Process results
        file_results_html = []
        total_files = len(results)
        files_with_issues = 0
        total_issues = 0
        high_issues = 0
        medium_issues = 0
        low_issues = 0
        total_score = 0
        scored_files = 0
        
        for result in results:
            # Access discrepancies from the nested structure
            analysis_data = result.get('analysis', {}).get('analysis', {})
            issues = analysis_data.get('discrepancies', [])
            total_issues += len(issues)
            
            if len(issues) > 0:
                files_with_issues += 1
            
            # Calculate score if available
            score_value = analysis_data.get('compliance_score')
            if score_value is not None:
                # Handle if compliance_score is a string
                if isinstance(score_value, str):
                    try:
                        score = float(score_value)
                    except (ValueError, TypeError):
                        score = 0
                else:
                    score = score_value
                    
                total_score += score
                scored_files += 1
                
            # Count issues by severity
            for issue in issues:
                severity = issue.get('severity', 'medium').lower()
                if severity == 'high':
                    high_issues += 1
                elif severity == 'medium':
                    medium_issues += 1
                elif severity == 'low':
                    low_issues += 1
            
            # Generate HTML for each file
            file_html = generate_file_result_html(result)
            file_results_html.append(file_html)
        
        # Calculate average score
        avg_score = round(total_score / scored_files, 1) if scored_files > 0 else 0
        
        # Determine score class for styling
        if avg_score >= 80:
            score_class = "success"
        elif avg_score >= 60:
            score_class = "warning"
        else:
            score_class = "danger"
        
        # Process style guide content
        safe_style_guide = "Style guide not available"
        if style_guide and style_guide.strip():
            try:
                # Convert Markdown to HTML
                safe_style_guide = markdown.markdown(style_guide)
                # No need to replace newlines since markdown converter handles this
            except Exception as e:
                # Fallback to basic formatting if markdown conversion fails
                safe_style_guide = style_guide.replace('{', '{{').replace('}', '}}').replace('<', '&lt;').replace('>', '&gt;')
                safe_style_guide = safe_style_guide.replace('\n', '<br>')
                click.echo(f"Warning: Could not render Markdown for style guide: {str(e)}")
        
        # HTML template with Bootstrap styling
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki.js Content Analysis Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .severity-high {{ color: #dc3545; }}
        .severity-medium {{ color: #fd7e14; }}
        .severity-low {{ color: #0d6efd; }}
        .style-guide-section {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: sans-serif;
        }}
        .style-guide-section h1 {{ font-size: 1.75rem; }}
        .style-guide-section h2 {{ font-size: 1.5rem; }}
        .style-guide-section h3 {{ font-size: 1.25rem; }}
        .style-guide-section h4 {{ font-size: 1.1rem; }}
        .style-guide-section code {{ background-color: #eee; padding: 2px 4px; border-radius: 3px; }}
        .style-guide-section pre {{ background-color: #eee; padding: 10px; border-radius: 5px; overflow: auto; }}
        
        /* Fix for accordion button spacing */
        .accordion-button {{ padding-right: 25px; }}
        
        /* Fix for percentage badge alignment */
        .file-info-container {{ 
            display: flex; 
            align-items: center; 
            margin-left: auto;
            min-width: 160px;
            justify-content: flex-end;
            margin-right: 15px;
        }}
        .file-info-container .badge {{ 
            margin-left: 8px;
            min-width: 60px;
            text-align: center;
        }}
        .file-title {{ 
            flex-grow: 1; 
            margin-right: 15px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        /* Control buttons styles */
        .control-buttons {{ 
            margin-bottom: 15px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        /* Search box style */
        .search-container {{ 
            max-width: 300px;
            margin-left: auto;
        }}
        
        /* Fixed height for accordion container with scrolling */
        .accordion-container {{ 
            max-height: 800px;
            overflow-y: auto;
            margin-bottom: 20px;
        }}
        
        /* Sort indicator */
        .sort-indicator {{ font-size: 0.8em; margin-left: 5px; }}
        
        /* Severity filter styles */
        .severity-filter {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 12px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        
        .severity-filter label {{
            margin-bottom: 0;
            display: flex;
            align-items: center;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        
        .severity-filter input {{
            margin-right: 4px;
        }}
        
        .severity-badge {{
            width: 12px;
            height: 12px;
            display: inline-block;
            border-radius: 50%;
            margin-right: 4px;
        }}
        
        .severity-high-badge {{ background-color: #dc3545; }}
        .severity-medium-badge {{ background-color: #fd7e14; }}
        .severity-low-badge {{ background-color: #0d6efd; }}
        
        /* Hide items that don't match filter */
        .accordion-item.filtered {{ display: none !important; }}
        
        /* Styling for badges with filtered issues */
        .filtered-issues {{ 
            position: relative;
            border: 1px dashed #fff;
            cursor: help;
        }}
        
        /* Make filtered status more obvious */
        .filtered-issues::after {{
            content: '*';
            position: absolute;
            top: -2px;
            right: -2px;
            font-size: 10px;
            color: #fff;
        }}
    </style>
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">Wiki.js Content Analysis Report</h1>
        
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h2 class="h5 mb-0">Summary</h2>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Total Files:</strong> {total_files}</p>
                        <p><strong>Files with Issues:</strong> {files_with_issues}</p>
                        <p><strong>Total Issues:</strong> {total_issues}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>High Issues:</strong> <span class="severity-high">{high_issues}</span></p>
                        <p><strong>Medium Issues:</strong> <span class="severity-medium">{medium_issues}</span></p>
                        <p><strong>Low Issues:</strong> <span class="severity-low">{low_issues}</span></p>
                    </div>
                </div>
                <div class="mt-3">
                    <h5>Overall Compliance Score</h5>
                    <div class="progress">
                        <div class="progress-bar bg-{score_class}" role="progressbar" style="width: {avg_score}%;" 
                             aria-valuenow="{avg_score}" aria-valuemin="0" aria-valuemax="100">{avg_score}%</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Controls for the accordion -->
        <div class="control-buttons">
            <button id="expandAll" class="btn btn-outline-primary btn-sm">
                <i class="bi bi-chevron-down"></i> Expand All
            </button>
            <button id="collapseAll" class="btn btn-outline-primary btn-sm">
                <i class="bi bi-chevron-up"></i> Collapse All
            </button>
            <div class="dropdown">
                <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" id="sortDropdown" 
                        data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-sort-down"></i> Sort
                </button>
                <ul class="dropdown-menu" aria-labelledby="sortDropdown">
                    <li><a class="dropdown-item sort-option" href="#" data-sort="name-asc">Name A-Z</a></li>
                    <li><a class="dropdown-item sort-option" href="#" data-sort="name-desc">Name Z-A</a></li>
                    <li><a class="dropdown-item sort-option" href="#" data-sort="score-asc">Score (Low to High)</a></li>
                    <li><a class="dropdown-item sort-option" href="#" data-sort="score-desc">Score (High to Low)</a></li>
                    <li><a class="dropdown-item sort-option" href="#" data-sort="issues-asc">Issues (Low to High)</a></li>
                    <li><a class="dropdown-item sort-option" href="#" data-sort="issues-desc">Issues (High to Low)</a></li>
                </ul>
            </div>
            <div class="severity-filter">
                <span>Severity:</span>
                <label title="High severity issues">
                    <input type="checkbox" id="filterHigh" checked class="severity-checkbox" data-severity="high">
                    <span class="severity-badge severity-high-badge"></span> High
                </label>
                <label title="Medium severity issues">
                    <input type="checkbox" id="filterMedium" checked class="severity-checkbox" data-severity="medium">
                    <span class="severity-badge severity-medium-badge"></span> Medium
                </label>
                <label title="Low severity issues">
                    <input type="checkbox" id="filterLow" checked class="severity-checkbox" data-severity="low">
                    <span class="severity-badge severity-low-badge"></span> Low
                </label>
            </div>
            <div class="search-container">
                <div class="input-group">
                    <input type="text" id="searchBox" class="form-control form-control-sm" placeholder="Search files...">
                    <button class="btn btn-outline-secondary btn-sm" type="button" id="clearSearch">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
            </div>
        </div>
        
        <div class="accordion-container">
            <div class="accordion mb-4" id="fileAccordion">
                {file_results}
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header bg-secondary text-white">
                <h2 class="h5 mb-0">Style Guide</h2>
            </div>
            <div class="card-body">
                <div class="style-guide-section">
                    {style_guide}
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Get elements
            const accordionEl = document.getElementById('fileAccordion');
            const expandAllBtn = document.getElementById('expandAll');
            const collapseAllBtn = document.getElementById('collapseAll');
            const searchBox = document.getElementById('searchBox');
            const clearSearchBtn = document.getElementById('clearSearch');
            const sortOptions = document.querySelectorAll('.sort-option');
            const severityCheckboxes = document.querySelectorAll('.severity-checkbox');
            
            // Store original order of accordion items
            const accordionItems = Array.from(accordionEl.querySelectorAll('.accordion-item'));
            const originalOrder = [...accordionItems];
            
            // Store current filter state
            const filterState = {{
                searchTerm: '',
                severities: {{ high: true, medium: true, low: true }}
            }};
            
            // Expand all function
            expandAllBtn.addEventListener('click', function() {{
                accordionItems.forEach(item => {{
                    if (!item.classList.contains('filtered')) {{
                        const collapseEl = item.querySelector('.accordion-collapse');
                        const bsCollapse = new bootstrap.Collapse(collapseEl, {{ toggle: false }});
                        bsCollapse.show();
                    }}
                }});
            }});
            
            // Collapse all function
            collapseAllBtn.addEventListener('click', function() {{
                accordionItems.forEach(item => {{
                    const collapseEl = item.querySelector('.accordion-collapse');
                    const bsCollapse = new bootstrap.Collapse(collapseEl, {{ toggle: false }});
                    bsCollapse.hide();
                }});
            }});
            
            // Apply all filters
            function applyFilters() {{
                // First update file visibility based on search term and if they have matching severity issues
                accordionItems.forEach(item => {{
                    // Start with true, then check each condition
                    let shouldShow = true;
                    
                    // Check search term
                    if (filterState.searchTerm) {{
                        const titleEl = item.querySelector('.file-title');
                        const title = titleEl ? titleEl.textContent.toLowerCase() : '';
                        shouldShow = shouldShow && title.includes(filterState.searchTerm);
                    }}
                    
                    // Check severities - only filter if the item has issues
                    const issuesCount = parseInt(item.querySelector('.badge.bg-primary').textContent);
                    if (issuesCount > 0) {{
                        // Get all issue severities in this accordion item
                        const issueCards = item.querySelectorAll('.issue-card');
                        
                        // If we have issues, check that at least one matches our filter
                        if (issueCards.length > 0) {{
                            let hasMatchingSeverity = false;
                            let visibleIssuesCount = 0;
                            
                            // Now filter the individual issue cards
                            issueCards.forEach(card => {{
                                let severity = 'medium'; // Default
                                if (card.classList.contains('severity-high-issue')) severity = 'high';
                                else if (card.classList.contains('severity-medium-issue')) severity = 'medium';
                                else if (card.classList.contains('severity-low-issue')) severity = 'low';
                                
                                // Show/hide this specific issue card based on filter
                                if (filterState.severities[severity]) {{
                                    card.style.display = '';
                                    hasMatchingSeverity = true;
                                    visibleIssuesCount++;
                                }} else {{
                                    card.style.display = 'none';
                                }}
                            }});
                            
                            // Update the issues count badge to reflect visible issues
                            const badgeEl = item.querySelector('.badge.bg-primary');
                            if (badgeEl) {{
                                badgeEl.textContent = `${{visibleIssuesCount}} issues`;
                                // Optionally, add a visual cue if some issues are filtered
                                if (visibleIssuesCount < issuesCount) {{
                                    badgeEl.setAttribute('title', `Showing ${{visibleIssuesCount}} of ${{issuesCount}} issues (some filtered by severity)`);
                                    badgeEl.classList.add('filtered-issues');
                                }} else {{
                                    badgeEl.removeAttribute('title');
                                    badgeEl.classList.remove('filtered-issues');
                                }}
                            }}
                            
                            // Hide the file completely if no issues match the filter
                            shouldShow = shouldShow && hasMatchingSeverity;
                        }}
                    }}
                    
                    // Apply the visibility to the file
                    item.classList.toggle('filtered', !shouldShow);
                }});
                
                // Update the UI to show how many items are visible
                updateFilterCounts();
            }}
            
            // Update filter counts in UI
            function updateFilterCounts() {{
                const visibleItems = accordionItems.filter(item => !item.classList.contains('filtered')).length;
                const totalItems = accordionItems.length;
                
                // Update sort dropdown to show counts
                document.getElementById('sortDropdown').innerHTML = 
                    `<i class="bi bi-sort-down"></i> Sort (${{visibleItems}}/${{totalItems}})`;
            }}
            
            // Search function
            searchBox.addEventListener('input', function() {{
                filterState.searchTerm = this.value.toLowerCase();
                applyFilters();
            }});
            
            // Clear search
            clearSearchBtn.addEventListener('click', function() {{
                searchBox.value = '';
                filterState.searchTerm = '';
                applyFilters();
            }});
            
            // Severity filter function
            severityCheckboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const severity = this.getAttribute('data-severity');
                    filterState.severities[severity] = this.checked;
                    applyFilters();
                }});
            }});
            
            // Sort functions
            sortOptions.forEach(option => {{
                option.addEventListener('click', function(e) {{
                    e.preventDefault();
                    const sortType = this.getAttribute('data-sort');
                    
                    // Sort the items
                    const sortedItems = [...accordionItems].sort((a, b) => {{
                        if (sortType === 'name-asc' || sortType === 'name-desc') {{
                            const titleA = a.querySelector('.file-title').textContent.toLowerCase();
                            const titleB = b.querySelector('.file-title').textContent.toLowerCase();
                            return sortType === 'name-asc' ? 
                                titleA.localeCompare(titleB) : 
                                titleB.localeCompare(titleA);
                        }}
                        
                        if (sortType === 'score-asc' || sortType === 'score-desc') {{
                            const scoreA = parseFloat(a.querySelector('.badge.bg-success, .badge.bg-warning, .badge.bg-danger').textContent);
                            const scoreB = parseFloat(b.querySelector('.badge.bg-success, .badge.bg-warning, .badge.bg-danger').textContent);
                            return sortType === 'score-asc' ? scoreA - scoreB : scoreB - scoreA;
                        }}
                        
                        if (sortType === 'issues-asc' || sortType === 'issues-desc') {{
                            const issuesTextA = a.querySelector('.badge.bg-primary').textContent;
                            const issuesTextB = b.querySelector('.badge.bg-primary').textContent;
                            const issuesA = parseInt(issuesTextA.split(' ')[0]);
                            const issuesB = parseInt(issuesTextB.split(' ')[0]);
                            return sortType === 'issues-asc' ? issuesA - issuesB : issuesB - issuesA;
                        }}
                        
                        return 0;
                    }});
                    
                    // Update the DOM
                    accordionEl.innerHTML = '';
                    sortedItems.forEach(item => accordionEl.appendChild(item));
                    
                    // Update dropdown button text with current sort and visible items count
                    const visibleItems = sortedItems.filter(item => !item.classList.contains('filtered')).length;
                    const totalItems = sortedItems.length;
                    document.getElementById('sortDropdown').innerHTML = 
                        `<i class="bi bi-sort-down"></i> Sort: ${{this.textContent}} (${{visibleItems}}/${{totalItems}})`;
                }});
            }});
            
            // Initialize filter counts
            updateFilterCounts();
        }});
    </script>
</body>
</html>
"""
        
        # Combine all HTML parts
        html_content = html_template.format(
            total_files=total_files,
            files_with_issues=files_with_issues,
            total_issues=total_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            avg_score=avg_score,
            score_class=score_class,
            file_results="\n".join(file_results_html),
            style_guide=safe_style_guide
        )
        
        # Write HTML to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        import traceback
        print(f"Detailed error in HTML report generation:\n{traceback.format_exc()}")
        raise Exception(f"Error creating HTML report: {str(e)}")

def generate_file_result_html(result: Dict[str, Any]) -> str:
    """
    Generate HTML for a single file's analysis result.
    
    Args:
        result: Analysis result for a single file
        
    Returns:
        HTML string for the file result
    """
    title = result.get("title", "Untitled")
    path = result.get("path", "unknown")
    
    # Access discrepancies from the nested structure
    analysis_data = result.get("analysis", {}).get("analysis", {})
    issues = analysis_data.get("discrepancies", [])
    
    # Try to get compliance score from different possible locations
    compliance_score = analysis_data.get("compliance_score", 0)
    # Handle if compliance_score is a string
    if isinstance(compliance_score, str):
        try:
            compliance_score = float(compliance_score)
        except (ValueError, TypeError):
            compliance_score = 0
    
    # Generate a unique ID for this file's accordion item
    file_id = f"file_{path.replace('/', '_').replace('.', '_').replace(' ', '_')}"
    
    # Determine score class for styling
    if compliance_score >= 80:
        score_class = "success"
    elif compliance_score >= 60:
        score_class = "warning"
    else:
        score_class = "danger"
    
    # Generate HTML for issues
    issues_html = []
    for i, issue in enumerate(issues):
        severity = issue.get('severity', 'medium').lower()
        severity_class = "severity-high" if severity == "high" else \
                         "severity-medium" if severity == "medium" else \
                         "severity-low"
        
        issue_html = f"""
        <div class="card mb-2 issue-card severity-{severity}-issue">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span class="{severity_class}">{severity.capitalize()} Severity</span>
                <span>Location: {issue.get('location', 'Unknown')}</span>
            </div>
            <div class="card-body">
                <h5>{issue.get('issue', 'No description')}</h5>
                <p><strong>Suggestion:</strong> {issue.get('suggestion', 'No suggestion')}</p>
            </div>
        </div>
        """
        issues_html.append(issue_html)
    
    # If no issues, show a success message
    if not issues:
        issues_content = """
        <div class="alert alert-success">
            No issues found. This file follows the style guide!
        </div>
        """
    else:
        issues_content = "\n".join(issues_html)
    
    # Final HTML for this file
    file_html = f"""
    <div class="accordion-item">
        <h2 class="accordion-header" id="heading_{file_id}">
            <button class="accordion-button {'collapsed' if len(issues) == 0 else ''}" type="button" 
                    data-bs-toggle="collapse" data-bs-target="#collapse_{file_id}" 
                    aria-expanded="{str(len(issues) > 0).lower()}" aria-controls="collapse_{file_id}">
                <span class="file-title">{title} <small class="text-muted">({path})</small></span>
                <div class="file-info-container">
                    <span class="badge bg-{score_class}">{compliance_score}%</span>
                    <span class="badge bg-primary">{len(issues)} issues</span>
                </div>
            </button>
        </h2>
        <div id="collapse_{file_id}" class="accordion-collapse collapse {'show' if len(issues) > 0 else ''}" 
             aria-labelledby="heading_{file_id}" data-bs-parent="#fileAccordion">
            <div class="accordion-body">
                {issues_content}
            </div>
        </div>
    </div>
    """
    
    return file_html

@cli.command('list-models')
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

@cli.command('report')
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False), required=False)
@click.option('--output', '-o', help='Output HTML report path (default: analysis_report.html)')
@click.option('--style-guide', help='Path to style guide file to include in report')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def generate_report(input_file: Optional[str], output: Optional[str], style_guide: Optional[str], config_file: Optional[str]):
    """Generate an HTML report from analysis results.
    
    INPUT_FILE is the path to the JSON analysis results file.
    If not provided, will use defaults from configuration.
    """
    # Load configuration if config file is specified
    config = {}
    config_path = config_file or DEFAULT_CONFIG_PATH
    if os.path.exists(config_path):
        config = load_config(config_path)
        click.echo(f"✓ Loaded configuration from {config_path}")
    
    # Determine input file
    if not input_file:
        input_file = "analysis_results.json"  # Default name
        
        # If we have a config, check for custom analysis output location
        if config and 'gemini' in config:
            # Use output from analyze command if available
            input_file = config.get('gemini', {}).get('analysis_output', input_file)
    
    if not os.path.exists(input_file):
        click.echo(f"Error: Results file '{input_file}' not found.")
        click.echo("Run 'wikijs analyze' first or specify a valid results file.")
        return
    
    # Determine output file
    output_file = output or "analysis_report.html"
    
    # Load style guide if specified
    style_guide_content = None
    
    # Priority: 1. Command line arg, 2. Config file
    if style_guide:
        # User specified a custom style guide
        if os.path.exists(style_guide):
            try:
                with open(style_guide, 'r', encoding='utf-8') as f:
                    style_guide_content = f.read()
                click.echo(f"Loaded style guide from {style_guide}")
            except Exception as e:
                click.echo(f"Error loading style guide: {str(e)}")
        else:
            click.echo(f"Warning: Style guide file '{style_guide}' not found.")
    elif config and 'gemini' in config:
        # Try to get style guide from config
        config_style_guide = config.get('gemini', {}).get('style_guide_file')
        if config_style_guide and os.path.exists(config_style_guide):
            try:
                with open(config_style_guide, 'r', encoding='utf-8') as f:
                    style_guide_content = f.read()
                click.echo(f"Loaded style guide from {config_style_guide}")
            except Exception as e:
                click.echo(f"Error loading style guide: {str(e)}")
                
    # Check current directory for wiki_guide.md if not found yet
    if not style_guide_content:
        default_guide_paths = ["wiki_guide.md", "style_guide.md"]
        for guide_path in default_guide_paths:
            if os.path.exists(guide_path):
                try:
                    with open(guide_path, 'r', encoding='utf-8') as f:
                        style_guide_content = f.read()
                    click.echo(f"Loaded style guide from {guide_path}")
                    break
                except Exception as e:
                    click.echo(f"Error loading style guide: {str(e)}")
    
    # Load JSON results
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        click.echo(f"Loaded analysis results from {input_file}")
    except Exception as e:
        click.echo(f"Error loading analysis results: {str(e)}")
        return
    
    # Check if style guide has any potential template formatting issues
    if style_guide_content and ('{' in style_guide_content or '}' in style_guide_content):
        click.echo("Warning: Style guide contains curly braces which might cause formatting issues.")
        click.echo("We'll attempt to escape them automatically, but if you encounter problems,")
        click.echo("try using the debug-report command: 'wikijs debug-report analysis_results.json --style-guide your_style_guide.md'")
    
    # Generate report
    try:
        create_html_report(results, output_file, style_guide_content)
        click.echo(f"Report saved to {output_file}")
    except Exception as e:
        click.echo(f"Error creating HTML report: {str(e)}")
        click.echo("If you're experiencing formatting issues, try the debug-report command.")
        return
    
    click.echo(f"Report includes {len(results)} files with {count_issues(results)} issues in {count_files_with_issues(results)} files.")

@cli.command('debug-report')
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False), required=True)
@click.option('--output', '-o', help='Output HTML report path (default: debug_report.html)')
@click.option('--style-guide', help='Path to style guide file for debugging')
def debug_report(input_file: str, output: Optional[str], style_guide: Optional[str]):
    """Generate a simplified HTML report for debugging.
    
    INPUT_FILE is the path to the JSON analysis results file.
    """
    output_file = output or "debug_report.html"
    
    # Load JSON results
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        click.echo(f"Loaded analysis results from {input_file}")
    except Exception as e:
        click.echo(f"Error loading analysis results: {str(e)}")
        return
    
    # Load style guide if specified
    style_guide_content = None
    if style_guide:
        try:
            with open(style_guide, 'r', encoding='utf-8') as f:
                style_guide_content = f.read()
            click.echo(f"Loaded style guide from {style_guide}")
            
            # Important: Escape curly braces to prevent formatting issues
            style_guide_content = style_guide_content.replace('{', '{{').replace('}', '}}')
        except Exception as e:
            click.echo(f"Error loading style guide: {str(e)}")
    
    # Generate simple HTML report
    try:
        # Create a simplified HTML template
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Debug Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .file {{ margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; }}
        .issue {{ margin: 10px 0; padding: 5px; border-left: 3px solid #f00; }}
        .style-guide {{ background-color: #f8f9fa; padding: 10px; margin-top: 30px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>Debug Report</h1>
    <p>Total files: {total_files}</p>
    
    <div id="files">
        {file_results}
    </div>
    
    {style_guide_section}
</body>
</html>
"""
        
        # Process results in simplified format
        file_results_html = []
        for result in results:
            title = result.get("title", "Untitled")
            path = result.get("path", "unknown")
            issues = result.get("issues", [])
            
            issues_html = []
            for issue in issues:
                issue_html = f"""
                <div class="issue">
                    <strong>{issue.get('severity', 'medium').capitalize()}:</strong>
                    <p>{issue.get('issue', 'No description')}</p>
                </div>
                """
                issues_html.append(issue_html)
            
            file_html = f"""
            <div class="file">
                <h2>{title}</h2>
                <p>Path: {path}</p>
                <p>Issues: {len(issues)}</p>
                {"".join(issues_html) if issues else "<p>No issues found</p>"}
            </div>
            """
            file_results_html.append(file_html)
        
        # Style guide section
        if style_guide_content:
            style_guide_html = f"""
            <div class="style-guide">
                <h2>Style Guide (Debug View)</h2>
                <p>This shows the raw style guide content with HTML entities to help debug formatting issues.</p>
                <pre>{style_guide_content.replace('<', '&lt;').replace('>', '&gt;')}</pre>
            </div>
            """
        else:
            style_guide_html = ""
        
        # Combine HTML parts
        html_content = html_template.format(
            total_files=len(results),
            file_results="\n".join(file_results_html),
            style_guide_section=style_guide_html
        )
        
        # Write HTML to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        click.echo(f"Debug report saved to {output_file}")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        click.echo(f"Error creating debug report: {str(e)}")
        click.echo(f"Detailed error:\n{error_details}")
        return

def count_issues(results: List[Dict[str, Any]]) -> int:
    """Count the total number of issues in all results."""
    total = 0
    for result in results:
        # Issues are in analysis.analysis.discrepancies
        discrepancies = result.get('analysis', {}).get('analysis', {}).get('discrepancies', [])
        total += len(discrepancies)
    return total

def count_files_with_issues(results: List[Dict[str, Any]]) -> int:
    """Count the number of files that have issues."""
    return sum(1 for r in results if len(r.get('analysis', {}).get('analysis', {}).get('discrepancies', [])) > 0)

if __name__ == '__main__':
    cli() 
"""
Content analysis command for Wiki.js Exporter.
"""

import os
import json
import click
from typing import Optional, List, Dict, Any

from ..config import DEFAULT_CONFIG_PATH, load_config, create_sample_style_guide
from ..utils import load_env_variables, load_pages_from_file, load_pages_from_markdown, generate_sitemap
from ..gemini import GeminiAnalyzer
from .report import create_html_report

@click.command('analyze')
@click.option('--format', type=click.Choice(['json', 'markdown']), default='markdown', 
              help='Format of the input (json or markdown)')
@click.option('--output', help='Output JSON file path (default: analysis_results.json)')
@click.option('--report', help='Output HTML report path (default: analysis_report.html)')
@click.option('--input', help='Input file or directory path (for json or markdown)')
@click.option('--api-key', help='Google Gemini API key')
@click.option('--style-guide', help='Path to style guide file')
@click.option('--ai-guide', help='Path to AI-specific instructions file')
@click.option('--model', help='Gemini model to use (default: gemini-2.0-flash)')
@click.option('--delay', type=float, default=1.0, help='Delay between API calls in seconds (default: 1.0)')
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.option('--show-sitemap/--no-sitemap', default=False, help='Show generated sitemap before analysis')
@click.option('--enhanced-sitemap/--basic-sitemap', default=True, help='Use enhanced sitemap with additional metadata')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def analyze_content(format: str, output: Optional[str], report: Optional[str], input: Optional[str], 
                   api_key: Optional[str], style_guide: Optional[str], ai_guide: Optional[str], 
                   model: Optional[str], delay: float, debug: bool, show_sitemap: bool,
                   enhanced_sitemap: bool, config_file: Optional[str]):
    """Analyze exported wiki content for style guide compliance."""
    # Load environment variables
    env_url, env_token, env_gemini_key = load_env_variables()
    
    # Load configuration from file
    config = load_config(config_file)
    if config_file:
        click.echo(f"✓ Loaded configuration from {config_file}")
    
    # Precedence: 1) Command-line args, 2) Config file, 3) Environment variables
    gemini_api_key = api_key or config["gemini"].get("api_key") or env_gemini_key
    style_guide_file = style_guide or config["gemini"].get("style_guide_file", "wiki_style_guide.md")
    ai_guide_file = ai_guide or config["gemini"].get("ai_guide_file", "ai_instructions.md")
    gemini_model = model or config["gemini"].get("model", "gemini-2.0-flash")
    
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
            with open(style_guide_file, 'r', encoding='utf-8') as f:
                style_guide_content = f.read()
            click.echo(f"Using style guide from {style_guide_file}")
        except Exception as e:
            click.echo(f"Error reading style guide file: {str(e)}")
            return
    
    # Check if AI guide file exists
    ai_guide_content = None
    if os.path.exists(ai_guide_file):
        try:
            with open(ai_guide_file, 'r', encoding='utf-8') as f:
                ai_guide_content = f.read()
            click.echo(f"Using AI instructions from {ai_guide_file}")
        except Exception as e:
            click.echo(f"Warning: Could not read AI instructions file: {str(e)}")
    else:
        click.echo(f"Note: AI instructions file not found at {ai_guide_file}. Using only the style guide.")
    
    # Determine input source based on format
    input_source = input or default_input
    
    if not input_source or not os.path.exists(input_source):
        click.echo(f"Error: Input {'file' if format == 'json' else 'directory'} {input_source or '(not specified)'} not found.")
        return
    
    # Load content to analyze
    data = None
    if format == 'json':
        try:
            data = load_pages_from_file(input_source)
            click.echo(f"Loaded {len(data)} pages from JSON file: {input_source}")
        except Exception as e:
            click.echo(f"Error loading JSON data: {str(e)}")
            return
    elif format == 'markdown':
        try:
            data = load_pages_from_markdown(input_source)
            click.echo(f"Loaded {len(data)} pages from directory: {input_source}")
        except Exception as e:
            click.echo(f"Error loading Markdown data: {str(e)}")
            return
    
    if not data:
        click.echo("Error: No content loaded for analysis.")
        return
    
    # Generate and display sitemap if requested
    if show_sitemap:
        sitemap = generate_sitemap(data, enhanced=enhanced_sitemap)
        click.echo("\nGenerated Wiki Sitemap:")
        click.echo("------------------------")
        click.echo(sitemap)
        click.echo("------------------------\n")
        click.pause()
    
    # Initialize progress
    total_pages = len(data)
    click.echo(f"Analyzing {total_pages} pages using model: {gemini_model}")
    
    # Create analyzer with specified model
    analyzer = GeminiAnalyzer(api_key=gemini_api_key, model=gemini_model, debug=debug)
    
    # Set all pages for sitemap generation
    analyzer.set_all_pages(data)
    
    # Process files one by one to avoid rate limiting
    results = []
    success_count = 0
    error_count = 0
    
    with click.progressbar(data, label='Analyzing content', length=total_pages) as progress_data:
        for i, page in enumerate(progress_data):
            title = page.get('title', 'Untitled page')
            path = page.get('path', 'unknown')
            
            if debug:
                click.echo(f"\nAnalyzing page {i+1}/{total_pages}: {title} ({path})")
            
            # Extract content
            content = page.get('content', '')
            if not content:
                results.append({
                    "path": path,
                    "title": title,
                    "analysis": {
                        "success": False,
                        "message": "No content found in page"
                    }
                })
                error_count += 1
                continue
            
            # Analyze content
            try:
                analysis = analyzer.analyze_content(content, style_guide_content, ai_guide_content, page)
                
                # Create result
                result = {
                    "path": path,
                    "title": title,
                    "analysis": analysis
                }
                
                results.append(result)
                
                if analysis.get("success", False):
                    success_count += 1
                else:
                    error_count += 1
                    
                # Save intermediate results
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    if debug:
                        click.echo(f"Warning: Could not save intermediate results: {str(e)}")
                        
            except Exception as e:
                click.echo(f"\nError analyzing page {title}: {str(e)}")
                results.append({
                    "path": path,
                    "title": title,
                    "analysis": {
                        "success": False,
                        "message": f"Error during analysis: {str(e)}"
                    }
                })
                error_count += 1
    
    # Save final results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    click.echo(f"\nAnalysis complete. Results saved to {output_file}")
    click.echo(f"Summary: {success_count} pages analyzed successfully, {error_count} pages with errors")
    
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
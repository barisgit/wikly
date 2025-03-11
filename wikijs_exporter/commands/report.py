"""
Report generation command for Wiki.js Exporter.
"""

import os
import json
import click
from typing import Dict, List, Any, Optional
import datetime
from pathlib import Path
import re

# Add markdown parser library import
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    pass

# Import config loading utilities
from ..config import DEFAULT_CONFIG_PATH, load_config

@click.command('report')
@click.argument('input_file', required=False)
@click.option('--output', '-o', help='Output path for HTML report')
@click.option('--style-guide', help='Path to style guide file to include in the report')
@click.option('--config-file', help=f'Path to configuration file (default: {DEFAULT_CONFIG_PATH})')
def generate_report(input_file: Optional[str], output: Optional[str], style_guide: Optional[str], config_file: Optional[str]):
    """Generate an HTML report from existing analysis results."""
    # Determine input and output files
    default_input = "analysis_results.json"
    default_output = "analysis_report.html"
    
    input_path = input_file or default_input
    output_path = output or default_output
    
    # Load configuration from file
    config = load_config(config_file)
    if config_file:
        click.echo(f"✓ Loaded configuration from {config_file}")
    
    # Get style guide path from config if not provided
    style_guide_path = style_guide
    if not style_guide_path and 'gemini' in config:
        style_guide_path = config["gemini"].get("style_guide_file", "wiki_style_guide.md")
        if style_guide_path:
            click.echo(f"Using style guide path from config: {style_guide_path}")
    
    if not os.path.exists(input_path):
        click.echo(f"Error: Input file {input_path} not found.")
        return
    
    # Load analysis results
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        click.echo(f"Error loading analysis results: {str(e)}")
        return
    
    # Load style guide if provided
    style_guide_content = None
    if style_guide_path and os.path.exists(style_guide_path):
        try:
            with open(style_guide_path, 'r', encoding='utf-8') as f:
                style_guide_content = f.read()
            click.echo(f"Loaded style guide from {style_guide_path} ({len(style_guide_content)} characters)")
        except Exception as e:
            click.echo(f"Warning: Could not read style guide file: {str(e)}")
    else:
        if style_guide_path:
            click.echo(f"Warning: Style guide file not found at {style_guide_path}")
        else:
            click.echo("No style guide specified. Report will not include style guide content.")
    
    # Create HTML report
    try:
        create_html_report(results, output_path, style_guide_content)
        click.echo(f"HTML report generated: {output_path}")
    except Exception as e:
        click.echo(f"Error generating report: {str(e)}")


def create_html_report(results: List[Dict[str, Any]], output_file: str, style_guide: Optional[str] = None):
    """
    Create an HTML report from analysis results.
    
    Args:
        results: List of analysis results
        output_file: Output file path
        style_guide: Optional style guide content to include
    """
    # Count files with issues
    files_with_issues = sum(1 for r in results if r.get("analysis", {}).get("success", False) and 
                           len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) > 0)
    
    total_files = len(results)
    total_issues = sum(len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) 
                      for r in results if r.get("analysis", {}).get("success", False))
    
    # Calculate average compliance score
    compliance_scores = [r.get("analysis", {}).get("analysis", {}).get("compliance_score", 0) 
                       for r in results if r.get("analysis", {}).get("success", False)]
    
    # Convert scores to float where possible
    numeric_scores = []
    for score in compliance_scores:
        try:
            numeric_scores.append(float(score))
        except (ValueError, TypeError):
            pass
    
    avg_compliance = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0
    
    # Count issues by severity
    high_issues = 0
    medium_issues = 0
    low_issues = 0
    
    for result in results:
        if not result.get("analysis", {}).get("success", False):
            continue
        
        discrepancies = result.get("analysis", {}).get("analysis", {}).get("discrepancies", [])
        for issue in discrepancies:
            severity = issue.get("severity", "").lower()
            if severity == "high":
                high_issues += 1
            elif severity == "medium":
                medium_issues += 1
            elif severity == "low":
                low_issues += 1
    
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format results for different views
    # Group by folder for sitemap view
    folder_structure = {}
    for result in results:
        path = result.get("path", "")
        if not path:
            continue
            
        # Break path into parts
        parts = path.split('/')
        
        # Navigate the folder structure and create it if it doesn't exist
        current = folder_structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # Last part (file)
                if '_files' not in current:
                    current['_files'] = []
                current['_files'].append(result)
            else:  # Folder
                if part not in current:
                    current[part] = {}
                current = current[part]
    
    # Sort results by compliance score (from worst to best)
    sorted_by_score = sorted(
        results, 
        key=lambda r: (
            float(r.get("analysis", {}).get("analysis", {}).get("compliance_score", 100))
            if r.get("analysis", {}).get("success", False) and r.get("analysis", {}).get("analysis", {}).get("compliance_score", "")
            else 100
        )
    )
    
    # Create HTML report
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki Content Analysis Report</title>
    <style>
        :root {{
            --primary-color: #3498db;
            --success-color: #2ecc71;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --light-bg: #f8f9fa;
            --dark-bg: #343a40;
            --text-color: #333;
            --light-text: #f8f9fa;
            --border-color: #dee2e6;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }}
        
        header {{
            background-color: var(--primary-color);
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        h1, h2, h3 {{
            margin-top: 1.5em;
            font-weight: 600;
        }}
        
        header h1 {{
            margin-top: 0;
        }}
        
        .summary {{
            background-color: var(--light-bg);
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .summary-card {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-top: 3px solid var(--primary-color);
        }}
        
        .severity-high {{
            border-top-color: var(--danger-color);
        }}
        
        .severity-medium {{
            border-top-color: var(--warning-color);
        }}
        
        .severity-low {{
            border-top-color: var(--success-color);
        }}
        
        .file {{
            border: 1px solid var(--border-color);
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .file-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        
        .file-path {{
            color: #777;
            font-size: 0.9em;
            word-break: break-all;
        }}
        
        .issue {{
            background-color: var(--light-bg);
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid var(--warning-color);
        }}
        
        .issue.high {{
            border-left-color: var(--danger-color);
            background-color: rgba(231, 76, 60, 0.05);
        }}
        
        .issue.medium {{
            border-left-color: var(--warning-color);
            background-color: rgba(243, 156, 18, 0.05);
        }}
        
        .issue.low {{
            border-left-color: var(--success-color);
            background-color: rgba(46, 204, 113, 0.05);
        }}
        
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        
        .severity {{
            font-size: 0.8em;
            padding: 3px 8px;
            border-radius: 3px;
            color: white;
            text-transform: uppercase;
            font-weight: bold;
        }}
        
        .severity.high {{
            background-color: var(--danger-color);
        }}
        
        .severity.medium {{
            background-color: var(--warning-color);
        }}
        
        .severity.low {{
            background-color: var(--success-color);
        }}
        
        .suggestion {{
            background-color: rgba(52, 152, 219, 0.05);
            padding: 15px;
            margin-top: 10px;
            border-radius: 5px;
            border-left: 4px solid var(--primary-color);
        }}
        
        .progress-bar {{
            height: 15px;
            background-color: #e0e0e0;
            border-radius: 10px;
            margin: 10px 0;
            overflow: hidden;
        }}
        
        .progress {{
            height: 100%;
            border-radius: 10px;
            background-color: var(--success-color);
        }}
        
        .tab-container {{
            margin-bottom: 20px;
        }}
        
        .tab-buttons {{
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
        }}
        
        .tab-button {{
            padding: 10px 15px;
            background-color: var(--light-bg);
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
        }}
        
        .tab-button.active {{
            background-color: var(--primary-color);
            color: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .filters {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .filter-button {{
            padding: 5px 10px;
            background-color: var(--light-bg);
            border: 1px solid var(--border-color);
            border-radius: 3px;
            cursor: pointer;
        }}
        
        .filter-button.active {{
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }}
        
        .search-container {{
            margin-bottom: 20px;
        }}
        
        .search-input {{
            width: 100%;
            padding: 10px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            font-size: 1em;
        }}
        
        @media (max-width: 768px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            
            .file-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
        
        .no-issues {{
            text-align: center;
            padding: 50px;
            color: #777;
        }}
        
        .style-guide-container {{
            margin-top: 30px;
            padding: 20px;
            background-color: var(--light-bg);
            border-radius: 5px;
        }}
        
        .timestamp {{
            text-align: right;
            font-size: 0.8em;
            color: #ccc;
            margin-top: 10px;
        }}
        
        .issue-location {{
            background-color: rgba(0,0,0,0.03);
            padding: 5px 10px;
            border-radius: 3px;
            font-family: monospace;
            word-break: break-all;
        }}
        
        summary {{
            cursor: pointer;
            font-weight: 600;
            padding: 10px 0;
        }}
        
        details {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        
        /* New styles for sitemap view */
        .sitemap-container {{
            margin-top: 20px;
        }}
        
        .sitemap-folder {{
            margin-bottom: 5px;
        }}
        
        .sitemap-folder-header {{
            cursor: pointer;
            padding: 8px;
            border-radius: 4px;
            background-color: #f8f9fa;
            display: flex;
            align-items: center;
        }}
        
        .sitemap-folder.has-issues > .sitemap-folder-header {{
            background-color: rgba(243, 156, 18, 0.1);
        }}
        
        .sitemap-content {{
            margin-left: 20px;
            padding-left: 10px;
            border-left: 1px dashed #ddd;
            display: none;
        }}
        
        .sitemap-toggle {{
            margin-right: 8px;
            font-size: 10px;
            transition: transform 0.2s;
        }}
        
        .sitemap-folder.expanded > .sitemap-folder-header .sitemap-toggle {{
            transform: rotate(90deg);
        }}
        
        .sitemap-folder.expanded > .sitemap-content {{
            display: block;
        }}
        
        .sitemap-name {{
            flex-grow: 1;
            font-weight: 500;
        }}
        
        .sitemap-count {{
            color: #e74c3c;
            font-size: 0.85em;
            margin-left: 10px;
        }}
        
        .sitemap-file {{
            padding: 5px 8px;
            margin: 5px 0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            cursor: pointer;
        }}
        
        .sitemap-file:hover {{
            background-color: #f5f5f5;
        }}
        
        .sitemap-file.has-issues {{
            background-color: rgba(46, 204, 113, 0.05);
        }}
        
        .sitemap-file.severity-medium {{
            background-color: rgba(243, 156, 18, 0.05);
        }}
        
        .sitemap-file.severity-high {{
            background-color: rgba(231, 76, 60, 0.05);
        }}
        
        .sitemap-details {{
            font-size: 0.85em;
            color: #777;
        }}
        
        .sitemap-no-issues {{
            font-size: 0.85em;
            color: #2ecc71;
        }}
        
        .sitemap-error {{
            background-color: rgba(231, 76, 60, 0.05);
        }}
        
        .sitemap-error-msg {{
            font-size: 0.85em;
            color: #e74c3c;
        }}
        
        .severity-pill {{
            display: inline-block;
            padding: 1px 6px;
            border-radius: 10px;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 5px;
        }}
        
        .severity-pill.high {{
            background-color: var(--danger-color);
        }}
        
        .severity-pill.medium {{
            background-color: var(--warning-color);
        }}
        
        .severity-pill.low {{
            background-color: var(--success-color);
        }}
        
        /* File details overlay */
        .overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            overflow: auto;
        }}
        
        .overlay-content {{
            position: relative;
            background-color: white;
            margin: 50px auto;
            padding: 20px;
            width: 80%;
            max-width: 1000px;
            border-radius: 5px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        
        .close-button {{
            position: absolute;
            top: 10px;
            right: 20px;
            font-size: 28px;
            font-weight: bold;
            color: #aaa;
            cursor: pointer;
        }}
        
        .close-button:hover {{
            color: #555;
        }}
        
        /* Make files in All Files tab clickable */
        .file-header {{
            cursor: pointer;
        }}
        
        .file-header:hover {{
            background-color: rgba(0,0,0,0.02);
        }}
    </style>
</head>
<body>
    <header>
        <h1>Wiki Content Analysis Report</h1>
        <p>Style guide compliance analysis for wiki content</p>
        <p class="timestamp">Generated: {timestamp}</p>
    </header>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Files Analyzed</h3>
                <p class="large-number">{total_files}</p>
                <p>{files_with_issues} files with issues ({round(files_with_issues/total_files*100 if total_files else 0, 1)}% of total)</p>
            </div>
            
            <div class="summary-card">
                <h3>Compliance Score</h3>
                <p class="large-number">{round(avg_compliance, 1)}/100</p>
                <div class="progress-bar">
                    <div class="progress" style="width: {min(100, max(0, avg_compliance))}%;"></div>
                </div>
            </div>
            
            <div class="summary-card">
                <h3>Issue Severity</h3>
                <p><span class="severity high">High</span> {high_issues} issues</p>
                <p><span class="severity medium">Medium</span> {medium_issues} issues</p>
                <p><span class="severity low">Low</span> {low_issues} issues</p>
            </div>
        </div>
    </div>
    
    <div class="tab-container">
        <div class="tab-buttons">
            <button class="tab-button active" data-tab="issues-tab">Issues ({files_with_issues})</button>
            <button class="tab-button" data-tab="all-files-tab">All Files ({total_files})</button>
            <button class="tab-button" data-tab="sitemap-tab">Sitemap View</button>
            <button class="tab-button" data-tab="style-guide-tab">Style Guide</button>
        </div>
        
        <div class="tab-content active" id="issues-tab">
            <div class="search-container">
                <input type="text" class="search-input" placeholder="Search in issues...">
            </div>
            
            <div class="filters">
                <span>Filter by severity:</span>
                <button class="filter-button active" data-severity="all">All</button>
                <button class="filter-button" data-severity="high">High</button>
                <button class="filter-button" data-severity="medium">Medium</button>
                <button class="filter-button" data-severity="low">Low</button>
            </div>
"""
    
    # Sort results by number of issues (most issues first)
    sorted_results = sorted(
        results, 
        key=lambda r: len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) if r.get("analysis", {}).get("success", False) else 0,
        reverse=True
    )
    
    # Add file sections for files with issues
    files_with_issues_count = 0
    
    for result in sorted_results:
        if not result.get("analysis", {}).get("success", False):
            continue
            
        analysis = result.get("analysis", {}).get("analysis", {})
        discrepancies = analysis.get("discrepancies", [])
        
        if not discrepancies:
            continue  # Skip files with no issues
        
        files_with_issues_count += 1
        file_path = result.get("path", "Unknown path")
        title = result.get("title", "Untitled page")
        compliance_score = analysis.get("compliance_score", "N/A")
        
        # Try to convert compliance score to number
        try:
            compliance_score = float(compliance_score)
            compliance_percent = min(100, max(0, compliance_score))
        except (ValueError, TypeError):
            compliance_percent = 0
        
        html += f"""
            <div class="file searchable-item">
                <div class="file-header">
                    <div>
                        <h3>{title}</h3>
                        <p class="file-path">{file_path}</p>
                    </div>
                    <div>
                        <p>Compliance Score: {compliance_score}/100</p>
                        <div class="progress-bar">
                            <div class="progress" style="width: {compliance_percent}%;"></div>
                        </div>
                    </div>
                </div>
                <p><strong>Summary:</strong> {analysis.get("summary", "No summary available")}</p>
                
                <h4>Discrepancies ({len(discrepancies)})</h4>
"""
        
        # Add issues
        for issue in discrepancies:
            severity = issue.get("severity", "medium").lower()
            location = issue.get("location", "Unknown location")
            suggestion = issue.get("suggestion", "No suggestion available")
            issue_text = issue.get("issue", "Issue")
            
            html += f"""
                <div class="issue {severity} severity-item" data-severity="{severity}">
                    <div class="issue-header">
                        <h4>{issue_text}</h4>
                        <span class="severity {severity}">{severity}</span>
                    </div>
                    <p><strong>Location:</strong> <span class="issue-location">{location}</span></p>
                    <div class="suggestion">
                        <strong>Suggestion:</strong> {suggestion}
                    </div>
                </div>
"""
        
        html += """
            </div>
"""
    
    if files_with_issues_count == 0:
        html += """
            <div class="no-issues">
                <h3>No issues found!</h3>
                <p>All analyzed files comply with the style guide.</p>
            </div>
"""
    
    # Add all files tab content
    html += """
        </div>
        
        <div class="tab-content" id="all-files-tab">
            <div class="search-container">
                <input type="text" class="search-input" placeholder="Search all files...">
            </div>
"""
    
    # Group files by compliance score range
    excellent_files = []
    good_files = []
    moderate_files = []
    needs_work_files = []
    error_files = []
    
    for result in results:
        if not result.get("analysis", {}).get("success", False):
            error_files.append(result)
            continue
            
        analysis = result.get("analysis", {}).get("analysis", {})
        compliance_score = analysis.get("compliance_score", 0)
        
        try:
            score = float(compliance_score)
            if score >= 90:
                excellent_files.append(result)
            elif score >= 75:
                good_files.append(result)
            elif score >= 50:
                moderate_files.append(result)
            else:
                needs_work_files.append(result)
        except (ValueError, TypeError):
            error_files.append(result)
    
    # Add files by category
    if excellent_files:
        html += """
            <details open>
                <summary>Excellent (90-100%)</summary>
        """
        
        for result in excellent_files:
            title = result.get("title", "Untitled")
            path = result.get("path", "Unknown path")
            analysis = result.get("analysis", {}).get("analysis", {})
            compliance_score = analysis.get("compliance_score", "N/A")
            discrepancies = len(analysis.get("discrepancies", []))
            
            html += f"""
                <div class="file-header searchable-item">
                    <div>
                        <h4>{title}</h4>
                        <p class="file-path">{path}</p>
                    </div>
                    <div>
                        <p>Score: {compliance_score}/100 ({discrepancies} issues)</p>
                    </div>
                </div>
            """
        
        html += """
            </details>
        """
    
    if good_files:
        html += """
            <details open>
                <summary>Good (75-89%)</summary>
        """
        
        for result in good_files:
            title = result.get("title", "Untitled")
            path = result.get("path", "Unknown path")
            analysis = result.get("analysis", {}).get("analysis", {})
            compliance_score = analysis.get("compliance_score", "N/A")
            discrepancies = len(analysis.get("discrepancies", []))
            
            html += f"""
                <div class="file-header searchable-item">
                    <div>
                        <h4>{title}</h4>
                        <p class="file-path">{path}</p>
                    </div>
                    <div>
                        <p>Score: {compliance_score}/100 ({discrepancies} issues)</p>
                    </div>
                </div>
            """
        
        html += """
            </details>
        """
    
    if moderate_files:
        html += """
            <details open>
                <summary>Moderate (50-74%)</summary>
        """
        
        for result in moderate_files:
            title = result.get("title", "Untitled")
            path = result.get("path", "Unknown path")
            analysis = result.get("analysis", {}).get("analysis", {})
            compliance_score = analysis.get("compliance_score", "N/A")
            discrepancies = len(analysis.get("discrepancies", []))
            
            html += f"""
                <div class="file-header searchable-item">
                    <div>
                        <h4>{title}</h4>
                        <p class="file-path">{path}</p>
                    </div>
                    <div>
                        <p>Score: {compliance_score}/100 ({discrepancies} issues)</p>
                    </div>
                </div>
            """
        
        html += """
            </details>
        """
    
    if needs_work_files:
        html += """
            <details open>
                <summary>Needs Work (0-49%)</summary>
        """
        
        for result in needs_work_files:
            title = result.get("title", "Untitled")
            path = result.get("path", "Unknown path")
            analysis = result.get("analysis", {}).get("analysis", {})
            compliance_score = analysis.get("compliance_score", "N/A")
            discrepancies = len(analysis.get("discrepancies", []))
            
            html += f"""
                <div class="file-header searchable-item">
                    <div>
                        <h4>{title}</h4>
                        <p class="file-path">{path}</p>
                    </div>
                    <div>
                        <p>Score: {compliance_score}/100 ({discrepancies} issues)</p>
                    </div>
                </div>
            """
        
        html += """
            </details>
        """
    
    if error_files:
        html += """
            <details open>
                <summary>Analysis Errors</summary>
        """
        
        for result in error_files:
            title = result.get("title", "Untitled")
            path = result.get("path", "Unknown path")
            error_msg = result.get("analysis", {}).get("message", "Unknown error")
            
            html += f"""
                <div class="file-header searchable-item">
                    <div>
                        <h4>{title}</h4>
                        <p class="file-path">{path}</p>
                    </div>
                    <div>
                        <p>Error: {error_msg}</p>
                    </div>
                </div>
            """
        
        html += """
            </details>
        """
    
    # Add new sitemap tab content
    html += """
        </div>
        
        <div class="tab-content" id="sitemap-tab">
            <div class="search-container">
                <input type="text" class="search-input" placeholder="Search in sitemap...">
            </div>
            <div class="sitemap-container">
    """
    
    # Recursive function to render the folder structure
    def render_folder(folder, name="Root", depth=0, path=""):
        folder_html = ""
        prefix = "    " * depth
        
        # Don't render root if it's not named
        if depth > 0 or name != "Root":
            current_path = path + ("/" if path else "") + name
            
            # Count issues in this folder and subfolders
            issue_count = 0
            for file in folder.get('_files', []):
                if file.get("analysis", {}).get("success", False):
                    issue_count += len(file.get("analysis", {}).get("analysis", {}).get("discrepancies", []))
            
            folder_class = "sitemap-folder"
            if issue_count > 0:
                folder_class += " has-issues"
                
            folder_html += f'{prefix}<div class="{folder_class}" data-path="{current_path}">\n'
            folder_html += f'{prefix}  <div class="sitemap-folder-header">\n'
            folder_html += f'{prefix}    <span class="sitemap-toggle">▶</span>\n'
            folder_html += f'{prefix}    <span class="sitemap-name">{name}</span>\n'
            if issue_count > 0:
                folder_html += f'{prefix}    <span class="sitemap-count">{issue_count} issue{"s" if issue_count != 1 else ""}</span>\n'
            folder_html += f'{prefix}  </div>\n'
            folder_html += f'{prefix}  <div class="sitemap-content">\n'
        else:
            current_path = path
            
        # Sort subdirectories alphabetically
        subdirs = [k for k in folder.keys() if k != '_files']
        subdirs.sort()
        
        # First render subdirectories
        for subdir in subdirs:
            folder_html += render_folder(folder[subdir], subdir, depth + 1, current_path)
        
        # Then render files
        if '_files' in folder:
            # Sort files by name
            files = sorted(folder['_files'], key=lambda f: f.get("title", "").lower())
            
            for file in files:
                title = file.get("title", "Untitled")
                file_path = file.get("path", "")
                
                # If no analysis or analysis failed, show as error
                if not file.get("analysis", {}).get("success", False):
                    error_msg = file.get("analysis", {}).get("message", "Analysis failed")
                    folder_html += f'{prefix}  <div class="sitemap-file sitemap-error" data-path="{file_path}">\n'
                    folder_html += f'{prefix}    <span class="sitemap-name">{title}</span>\n'
                    folder_html += f'{prefix}    <span class="sitemap-error-msg">{error_msg}</span>\n'
                    folder_html += f'{prefix}  </div>\n'
                    continue
                
                # Get analysis data
                analysis = file.get("analysis", {}).get("analysis", {})
                discrepancies = analysis.get("discrepancies", [])
                score = analysis.get("compliance_score", "N/A")
                
                # Calculate severity counts
                high = sum(1 for d in discrepancies if d.get("severity", "").lower() == "high")
                medium = sum(1 for d in discrepancies if d.get("severity", "").lower() == "medium")
                low = sum(1 for d in discrepancies if d.get("severity", "").lower() == "low")
                
                # Determine file class based on score
                file_class = "sitemap-file"
                if discrepancies:
                    file_class += " has-issues"
                    if float(score) < 50:
                        file_class += " severity-high"
                    elif float(score) < 75:
                        file_class += " severity-medium"
                    else:
                        file_class += " severity-low"
                
                # Create file entry
                folder_html += f'{prefix}  <div class="{file_class}" data-path="{file_path}" data-file-id="file-{file_path.replace("/", "-")}">\n'
                folder_html += f'{prefix}    <span class="sitemap-name">{title}</span>\n'
                
                if discrepancies:
                    folder_html += f'{prefix}    <span class="sitemap-details">'
                    folder_html += f'Score: {score}/100'
                    
                    if high > 0:
                        folder_html += f' <span class="severity-pill high">{high}</span>'
                    if medium > 0:
                        folder_html += f' <span class="severity-pill medium">{medium}</span>'
                    if low > 0:
                        folder_html += f' <span class="severity-pill low">{low}</span>'
                        
                    folder_html += '</span>\n'
                else:
                    folder_html += f'{prefix}    <span class="sitemap-no-issues">No issues</span>\n'
                    
                folder_html += f'{prefix}  </div>\n'
        
        # Close the folder div if we opened one
        if depth > 0 or name != "Root":
            folder_html += f'{prefix}  </div>\n'
            folder_html += f'{prefix}</div>\n'
            
        return folder_html
    
    # Render the full folder structure
    html += render_folder(folder_structure)
    
    html += """
            </div>
        </div>
    """
    
    # Add style guide tab
    html += """
        </div>
        
        <div class="tab-content" id="style-guide-tab">
            <div class="style-guide-container">
"""
    
    if style_guide:
        # Strip YAML frontmatter if present
        style_guide_content = strip_yaml_frontmatter(style_guide)
        
        # Convert Markdown to HTML
        if HAS_MARKDOWN:
            # Use the markdown library for better conversion
            style_guide_html = markdown.markdown(style_guide_content, extensions=['tables', 'fenced_code'])
        else:
            # Fallback to simple conversion if markdown library not available
            style_guide_html = simple_markdown_to_html(style_guide_content)
        
        html += f"""
                <div class="style-guide-content">
                    {style_guide_html}
                </div>
                <style>
                    .style-guide-content {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                    }}
                    .style-guide-content h1, 
                    .style-guide-content h2, 
                    .style-guide-content h3, 
                    .style-guide-content h4 {{
                        margin-top: 1.5em;
                        margin-bottom: 0.8em;
                        font-weight: 600;
                        color: #2c3e50;
                    }}
                    .style-guide-content h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
                    .style-guide-content h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
                    .style-guide-content h3 {{ font-size: 1.25em; }}
                    .style-guide-content h4 {{ font-size: 1em; }}
                    .style-guide-content p, .style-guide-content li {{ font-size: 16px; margin-bottom: 6px; }}
                    .style-guide-content ul, .style-guide-content ol {{ padding-left: 2em; margin-bottom: 0.4em; }}
                    .style-guide-content code {{
                        font-family: 'Courier New', Courier, monospace;
                        padding: 0.2em 0.4em;
                        background-color: rgba(27,31,35,.05);
                        border-radius: 3px;
                        font-size: 85%;
                    }}
                    .style-guide-content pre {{
                        background-color: #f6f8fa;
                        border-radius: 3px;
                        padding: 8px;
                        overflow: auto;
                        line-height: 1.45;
                        margin-bottom: 16px;
                    }}
                    .style-guide-content pre code {{
                        background-color: transparent;
                        padding: 0;
                        margin: 0;
                        font-size: 100%;
                        word-break: normal;
                        white-space: pre;
                        overflow: visible;
                    }}
                    .style-guide-content a {{
                        color: #0366d6;
                        text-decoration: none;
                    }}
                    .style-guide-content a:hover {{
                        text-decoration: underline;
                    }}
                    .style-guide-content blockquote {{
                        padding: 0 1em;
                        color: #6a737d;
                        border-left: 0.25em solid #dfe2e5;
                        margin: 0 0 8px 0;
                    }}
                    .style-guide-content strong {{ font-weight: 600; }}
                    .style-guide-content em {{ font-style: italic; }}
                </style>
        """
    else:
        html += """
                <p>No style guide content available.</p>
        """
    
    html += """
            </div>
        </div>
    </div>
    
    <div id="file-details-overlay" class="overlay">
        <div class="overlay-content">
            <span class="close-button">&times;</span>
            <div id="file-details-content"></div>
        </div>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', () => {
                // Deactivate all tabs
                document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
                
                // Activate clicked tab
                button.classList.add('active');
                document.getElementById(button.dataset.tab).classList.add('active');
            });
        });
        
        // Make folders expandable in sitemap view
        document.querySelectorAll('.sitemap-folder-header').forEach(header => {
            header.addEventListener('click', e => {
                const folder = header.closest('.sitemap-folder');
                folder.classList.toggle('expanded');
                e.stopPropagation();
            });
        });
        
        // Pre-expand top level folders
        document.querySelectorAll('.sitemap-container > .sitemap-folder').forEach(folder => {
            folder.classList.add('expanded');
        });
        
        // Add file details view functionality
        const overlay = document.getElementById('file-details-overlay');
        const detailsContent = document.getElementById('file-details-content');
        const closeButton = document.querySelector('.close-button');
        
        // Close overlay when clicking the X
        closeButton.addEventListener('click', () => {
            overlay.style.display = 'none';
        });
        
        // Close overlay when clicking outside the content
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.style.display = 'none';
            }
        });
        
        // Add a helper function for querySelector with contains
        function querySelectorContains(baseSelector, text) {
            const elements = document.querySelectorAll(baseSelector);
            const results = [];
            
            elements.forEach(el => {
                if (el.textContent.includes(text)) {
                    results.push(el);
                }
            });
            
            return results;
        }
        
        // Open file details when clicking on a file in sitemap
        document.querySelectorAll('.sitemap-file').forEach(file => {
            file.addEventListener('click', () => {
                const fileId = file.dataset.fileId;
                if (!fileId) return;
                
                const fileId_clean = fileId.replace('file-', '').replace(/-/g, '/');
                const fileName = file.querySelector('.sitemap-name').textContent;
                
                // Find the matching file from all files or issues tab
                let fileDetails = querySelectorContains('.file.searchable-item h3', fileName);
                if (fileDetails.length > 0) {
                    const fileElement = fileDetails[0].closest('.file');
                    if (fileElement) {
                        detailsContent.innerHTML = fileElement.outerHTML;
                        overlay.style.display = 'block';
                    }
                }
            });
        });
        
        // Make file headers in "All Files" tab clickable to show details
        document.querySelectorAll('#all-files-tab .file-header').forEach(header => {
            header.addEventListener('click', () => {
                const title = header.querySelector('h4').textContent;
                const path = header.querySelector('.file-path').textContent;
                
                // Find if this file has any issues
                let fileDetails = querySelectorContains('.file.searchable-item h3', title);
                if (fileDetails.length > 0) {
                    const fileElement = fileDetails[0].closest('.file');
                    if (fileElement) {
                        detailsContent.innerHTML = fileElement.outerHTML;
                        overlay.style.display = 'block';
                    }
                } else {
                    // If no issues found, just show basic info
                    detailsContent.innerHTML = `
                        <div class="file">
                            <div class="file-header">
                                <div>
                                    <h3>${title}</h3>
                                    <p class="file-path">${path}</p>
                                </div>
                            </div>
                            <p><strong>No issues found in this file.</strong></p>
                        </div>
                    `;
                    overlay.style.display = 'block';
                }
            });
        });
        
        // Search functionality
        document.querySelectorAll('.search-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const searchText = e.target.value.toLowerCase();
                const tabContent = e.target.closest('.tab-content');
                
                tabContent.querySelectorAll('.searchable-item').forEach(item => {
                    const text = item.textContent.toLowerCase();
                    if (text.includes(searchText)) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
                
                // Special handling for sitemap tab
                if (tabContent.id === 'sitemap-tab') {
                    // First hide all folders and files
                    tabContent.querySelectorAll('.sitemap-folder, .sitemap-file').forEach(item => {
                        item.style.display = 'none';
                    });
                    
                    // Then show those that match and their parents
                    tabContent.querySelectorAll('.sitemap-folder, .sitemap-file').forEach(item => {
                        const text = item.textContent.toLowerCase();
                        if (text.includes(searchText)) {
                            // Show this item
                            item.style.display = '';
                            
                            // If it's a folder, expand it
                            if (item.classList.contains('sitemap-folder')) {
                                item.classList.add('expanded');
                            }
                            
                            // Show all parent folders
                            let parent = item.parentElement;
                            while (parent) {
                                if (parent.classList.contains('sitemap-content')) {
                                    parent.style.display = 'block';
                                    const parentFolder = parent.closest('.sitemap-folder');
                                    if (parentFolder) {
                                        parentFolder.style.display = '';
                                        parentFolder.classList.add('expanded');
                                    }
                                }
                                parent = parent.parentElement;
                            }
                        }
                    });
                }
            });
        });
        
        // Severity filtering
        document.querySelectorAll('.filter-button').forEach(button => {
            button.addEventListener('click', () => {
                // Handle "All" button specially
                if (button.dataset.severity === 'all') {
                    const wasActive = button.classList.contains('active');
                    
                    // Clear all active states
                    document.querySelectorAll('.filter-button').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    
                    // If "All" was not active, activate it
                    if (!wasActive) {
                        button.classList.add('active');
                    }
                } else {
                    // Toggle active state for this button
                    button.classList.toggle('active');
                    
                    // Deactivate the "all" button when a specific filter is active
                    document.querySelector('.filter-button[data-severity="all"]').classList.remove('active');
                }
                
                // Get all active severity filters
                const activeFilters = Array.from(document.querySelectorAll('.filter-button.active'))
                    .map(btn => btn.dataset.severity)
                    .filter(severity => severity !== 'all');
                
                // If no filters are active, make "all" active
                if (activeFilters.length === 0) {
                    document.querySelector('.filter-button[data-severity="all"]').classList.add('active');
                }
                
                // Get the final set of active filters after potential adjustments
                const finalActiveFilters = Array.from(document.querySelectorAll('.filter-button.active'))
                    .map(btn => btn.dataset.severity);
                
                // Show/hide items based on active filters
                document.querySelectorAll('.severity-item').forEach(item => {
                    if (finalActiveFilters.includes('all') || finalActiveFilters.includes(item.dataset.severity)) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
                
                // Hide files that have no visible issues
                document.querySelectorAll('.file.searchable-item').forEach(file => {
                    const visibleIssues = Array.from(file.querySelectorAll('.severity-item')).filter(item => {
                        return item.style.display !== 'none';
                    });
                    const totalIssues = file.querySelectorAll('.severity-item');
                    
                    if (visibleIssues.length === 0 && totalIssues.length > 0) {
                        file.style.display = 'none';
                    } else {
                        file.style.display = '';
                    }
                });
            });
        });
    </script>
</body>
</html>
"""
    
    # Write HTML to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
    except Exception as e:
        raise Exception(f"Error writing HTML report: {str(e)}")

def strip_yaml_frontmatter(text: str) -> str:
    """
    Strip YAML frontmatter from text.
    
    Args:
        text: Text that may contain YAML frontmatter
        
    Returns:
        Text with frontmatter removed
    """
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return text

def simple_markdown_to_html(text: str) -> str:
    """
    Simple conversion of markdown to HTML for when the markdown library is not available.
    
    Args:
        text: Markdown text
        
    Returns:
        HTML text
    """
    # Convert headers
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    
    # Convert paragraphs
    paragraphs = re.split(r'\n\n+', text)
    for i, p in enumerate(paragraphs):
        if not p.startswith('<h') and not p.startswith('<ul') and not p.startswith('<ol'):
            paragraphs[i] = f'<p>{p}</p>'
    
    text = '\n\n'.join(paragraphs)
    
    # Convert bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # Convert lists
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', text, flags=re.MULTILINE)
    
    # Convert links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    
    # Convert code blocks
    text = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    return text 
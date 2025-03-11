"""
Report generation command for Wiki.js Exporter.
"""

import os
import json
import click
from typing import Dict, List, Any, Optional
import datetime
from pathlib import Path

@click.command('report')
@click.argument('input_file', required=False)
@click.option('--output', '-o', help='Output path for HTML report')
@click.option('--style-guide', help='Path to style guide file to include in the report')
@click.option('--config-file', help='Path to configuration file')
def generate_report(input_file: Optional[str], output: Optional[str], style_guide: Optional[str], config_file: Optional[str]):
    """Generate an HTML report from existing analysis results."""
    # Determine input and output files
    default_input = "analysis_results.json"
    default_output = "analysis_report.html"
    
    input_path = input_file or default_input
    output_path = output or default_output
    
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
    if style_guide and os.path.exists(style_guide):
        try:
            with open(style_guide, 'r', encoding='utf-8') as f:
                style_guide_content = f.read()
        except Exception as e:
            click.echo(f"Warning: Could not read style guide file: {str(e)}")
    
    # Create HTML report
    create_html_report(results, output_path, style_guide_content)
    click.echo(f"HTML report generated: {output_path}")


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
            color: #777;
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
    
    # Add style guide tab
    html += """
        </div>
        
        <div class="tab-content" id="style-guide-tab">
            <div class="style-guide-container">
"""
    
    if style_guide:
        # Simple conversion of markdown to HTML (very basic)
        style_guide_html = style_guide.replace("\n\n", "<br><br>")
        style_guide_html = style_guide_html.replace("# ", "<h1>").replace("\n## ", "</h1><h2>")
        style_guide_html = style_guide_html.replace("\n### ", "</h2><h3>").replace("\n#### ", "</h3><h4>")
        
        html += f"""
                <div class="style-guide-content">
                    {style_guide_html}
                </div>
        """
    else:
        html += """
                <p>No style guide content available.</p>
        """
    
    html += """
            </div>
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
            });
        });
        
        // Severity filtering
        document.querySelectorAll('.filter-button').forEach(button => {
            button.addEventListener('click', () => {
                // Update active button
                document.querySelectorAll('.filter-button').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                const severity = button.dataset.severity;
                
                // Show/hide items based on severity
                document.querySelectorAll('.severity-item').forEach(item => {
                    if (severity === 'all' || item.dataset.severity === severity) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
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
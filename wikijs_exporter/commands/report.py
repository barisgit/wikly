"""
Report generation commands for Wiki.js Exporter.
"""

import os
import json
import click
import markdown
from typing import Optional, Dict, Any, List

from ..config import DEFAULT_CONFIG_PATH, load_config, create_sample_style_guide

@click.command('report')
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
        
        # HTML template with Bootstrap styling (abbreviated for brevity)
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
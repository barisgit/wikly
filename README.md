# Wiki.js Exporter

A command-line tool to export content from a Wiki.js instance using the GraphQL API. This is a **read-only** tool that will not make any changes to your Wiki.js content.

## Features

- Export pages with metadata and content from Wiki.js
- Multiple output formats (JSON, Markdown, HTML)
- Easy to use command-line interface
- Support for environment variables and configuration files
- Read-only operation (won't modify your wiki)
- Export content with original paths and hierarchy
- Content analysis with Gemini AI to ensure style guide compliance

## Installation

### Using pip

```bash
pip install wikijs-exporter
```

### From source

```bash
git clone https://github.com/yourusername/wikijs-exporter.git
cd wikijs-exporter
pip install -e .
```

## Configuration

There are three ways to configure the Wiki.js Exporter:

1. **Configuration File**: Use the `wikijs init` command to generate a template configuration file.
2. **Command Line Options**: Pass options directly when running commands.
3. **Environment Variables**: Configure through environment variables.

The tool follows this precedence: Command Line > Config File > Environment Variables

### Configuration File

Run the following command to create a template configuration file:

```bash
wikijs init
```

This creates a `wikijs_config.yaml` file with the following structure:

```yaml
wikijs:
  host: https://your-wiki-instance.com
  api_key: YOUR_API_KEY_HERE

export:
  default_format: markdown
  default_output: wiki_pages
  delay: 0.1
  metadata_file: .wikijs_export_metadata.json

gemini:
  api_key: YOUR_GEMINI_API_KEY_HERE
```

You can specify a different path for the configuration file:

```bash
wikijs init --path custom_config.yaml
```

### Environment Variables

Set the following environment variables:

* `WIKIJS_HOST`: Base URL of your Wiki.js instance
* `WIKIJS_API_KEY`: API token with appropriate permissions
* `GEMINI_API_KEY`: Google Gemini API key (optional, for analysis features)

A convenient way to manage these variables is to create a `.env` file in your working directory:

```
WIKIJS_HOST=https://your-wiki-instance.com
WIKIJS_API_KEY=your-api-token
GEMINI_API_KEY=your-gemini-api-key
```

The tool will automatically load these variables when run.

## Usage

All commands accept a `--config-file` option to specify a custom configuration file:

```bash
wikijs <command> --config-file my_config.yaml
```

### Initialization

Generate a template configuration file:

```bash
wikijs init
```

This command creates three files:
1. `wikijs_config.yaml` - Main configuration file
2. `wiki_style_guide.md` - Sample style guide for content analysis
3. `ai_instructions.md` - AI-specific instructions for content analysis

Options:
* `--path`: Specify a custom location for the configuration file (default: wikijs_config.yaml)
* `--force`: Force overwrite if the files already exist

The configuration file includes settings for Wiki.js connection, export options, and AI analysis parameters.

### Test Connection

Verify your Wiki.js connection:

```bash
wikijs test
```

Options:
* `--url`: Override the Wiki.js URL
* `--token`: Override the API token
* `--config-file`: Path to custom configuration file

### List Pages

List all pages in your Wiki.js instance:

```bash
wikijs list
```

Options:
* `--url`: Override the Wiki.js URL
* `--token`: Override the API token
* `--config-file`: Path to custom configuration file

### Export Pages

Export all pages from Wiki.js:

```bash
wikijs export
```

Options:
* `--url`: Override the Wiki.js URL
* `--token`: Override the API token
* `--output`: Custom output location
* `--delay`: Adjust request delay (seconds)
* `--debug`: Enable debug output
* `--format`: Choose output format (json, markdown, html)
* `--incremental/--full`: Enable/disable incremental export (default: incremental)
* `--force-full`: Force a full export
* `--reset-hashes`: Reset all content hashes (forces recomputing)
* `--metadata-file`: Custom location for metadata file
* `--config-file`: Path to custom configuration file

### Analyze Content

Run semantic analysis on exported content:

```bash
wikijs analyze
```

This command uses the Gemini AI to analyze Wiki.js content against a style guide, identifying issues and suggesting improvements.

Options:
* `--format`: Input format (json, markdown)
* `--output`: Custom output location
* `--input`: Input file or directory
* `--api-key`: Google Gemini API key
* `--style-guide`: Custom path to style guide file
* `--ai-guide`: Custom path to AI instructions file
* `--config-file`: Path to custom configuration file

The analysis process:
1. Loads content from the specified source (JSON or Markdown files)
2. Reads the style guide and AI instructions (created by `wikijs init`)
3. Analyzes each page for style compliance
4. Generates a report with issues and suggestions

Results include:
- A summary of each page's compliance with the style guide
- Specific discrepancies with location and severity
- Suggested corrections for each issue
- An overall compliance score for each page

### Generate Report

Generate an HTML report from existing analysis results:

```bash
# Using an explicit input file
wikijs report analysis_results.json

# Using configuration defaults
wikijs report
```

This command takes previously generated analysis results (JSON) and creates a visual HTML report without needing to re-run the analysis.

Options:
* `--output`, `-o`: Custom output path for the HTML report (default: analysis_report.html)
* `--style-guide`: Path to style guide file to include in the report
* `--config-file`: Path to custom configuration file

If you don't specify an input file, the command will use the default paths from your configuration. This means you can simply run `wikijs report` after running `wikijs analyze` to generate an HTML report from the latest analysis results.

This is useful when:
- You want to generate a report with different formatting
- You need to share results with team members
- You've manually edited the analysis results
- You want to create multiple report versions from the same analysis

#### Style Guide and AI Instructions

The `wikijs init` command creates two files for content analysis:

1. **Style Guide** (`wiki_style_guide.md`): Contains human-readable guidelines for writing wiki content. This is the primary reference for what "good" content looks like.

2. **AI Instructions** (`ai_instructions.md`): Contains instructions specifically for the AI analyzer, such as how to prioritize issues, what context to consider, and special analysis requirements.

You can customize both files to match your organization's style requirements and content standards.

### Listing Pages (Metadata Only)

To fetch and save a list of all pages (without content):

```bash
wikijs list --output wiki_pages.json
```

### Exporting Pages with Content

To export all pages with their full content:

```bash
wikijs export --output wiki_export.json
```

By default, the exporter uses incremental mode, which only fetches content for pages that have been updated since the last export. This significantly speeds up subsequent exports.

The incremental export also detects local changes to exported files. If you modify a file after exporting it, the exporter will detect the change and re-fetch the content from Wiki.js during the next export.

To force a full export of all pages:

```bash
wikijs export --force-full
```

#### Export Formats

You can export in different formats using the `--format` option:

```bash
# Export as JSON (default)
wikijs export --format json

# Export as Markdown files
wikijs export --format markdown --output wiki_markdown

# Export as HTML files
wikijs export --format html --output wiki_html
```

#### Additional Export Options

```bash
# Set delay between API requests
wikijs export --delay 0.5

# Toggle between incremental and full exports
wikijs export --incremental  # Default, only fetches updated content
wikijs export --full         # Fetches all content

# Force a full export regardless of other settings
wikijs export --force-full

# Reset all content hashes (useful if having issues with local change detection)
wikijs export --reset-hashes

# Specify a custom metadata file location
wikijs export --metadata-file /path/to/metadata.json

# Enable verbose debugging output
wikijs export --debug
```

The exporter tracks metadata about previous exports in a `.wikijs_export_metadata.json` file, including:
- The last update time for each page
- Content hashes to detect local modifications
- Original paths and titles from Wiki.js

This allows the exporter to intelligently decide which pages need to be re-fetched during incremental exports, based on both server-side updates and local file changes.

##### Handling Edited Files

When you edit a file locally after exporting it, the exporter will detect the changes during the next export by comparing content hashes. There are three possible outcomes:

1. **Re-fetch the page**: By default, the exporter will detect local changes and re-fetch the page from Wiki.js.
2. **Keep local changes**: You can manually update the metadata file to match your local changes.
3. **Force reset all hashes**: Use `--reset-hashes` option to force recomputing all content hashes.

For complex workflows with many local edits, you may want to set up version control on your exported files.

### Analyzing Content for Style Compliance

The `analyze` command lets you check your wiki content against a style guide using Google's Gemini AI:

```bash
wikijs analyze path/to/exported/content style_guide.md
```

This will:
1. Process all Markdown and HTML files in the specified directory
2. Compare each file against the provided style guide
3. Generate a detailed report of discrepancies and suggestions
4. Save both raw results (JSON) and a readable HTML report

#### Incremental Analysis

By default, the analyze command uses incremental mode, which only analyzes pages that have changed since the last analysis. This significantly improves performance for large wikis:

```bash
# Incremental analysis (default)
wikijs analyze --incremental

# Force full analysis of all pages
wikijs analyze --full

# Force a full analysis regardless of other settings
wikijs analyze --force-full

# Reset all content hashes (useful if having issues with local change detection)
wikijs analyze --reset-hashes

# Specify a custom metadata file location
wikijs analyze --metadata-file /path/to/metadata.json
```

The analyzer tracks metadata about previous analyses in a `.wikijs_analysis_metadata.json` file, including:
- Content hashes to detect file changes
- Analysis timestamps for each page
- Issue counts and compliance scores

This allows the analyzer to intelligently decide which pages need to be re-analyzed, based on both content changes and previous analysis results.

#### Additional Options

```bash
# Set a custom output location for results
wikijs analyze content_dir style_guide.md --output analysis.json --report report.html

# Use a specific Gemini model
wikijs analyze content_dir style_guide.md --model gemini-1.5-pro

# Add delay between API calls to avoid rate limits
wikijs analyze content_dir style_guide.md --delay 2.0

# Provide a separate AI-specific guidance file
wikijs analyze content_dir style_guide.md --ai-guide ai_specific_guide.md

# Enable debug output
wikijs analyze content_dir style_guide.md --debug
```

#### AI Guide

You can optionally provide an AI-specific guidance file that contains instructions specifically for the AI analyzer, separate from the human-readable style guide. This allows you to:

- Give more technical instructions to the AI without cluttering the human style guide
- Provide examples of correct and incorrect content for better AI understanding
- Add contextual information that helps the AI make better judgments

Example usage:
```bash
wikijs analyze content_dir human_style_guide.md --ai-guide ai_specific_instructions.md
```

#### Rate Limiting Protection

The tool implements several strategies to handle Gemini API rate limits:

- Configurable delay between file processing (use `--delay` option)
- Random jitter added to delays to prevent synchronized requests
- Exponential backoff for 429 (Too Many Requests) errors
- Automatic retries when rate limits are hit (up to 5 attempts)

These features help ensure your analysis completes successfully even with large content sets.

#### Listing Available Models
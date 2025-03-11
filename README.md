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

You can configure the exporter using either:

1. Environment variables in a `.env` file:
   - `WIKIJS_HOST`: Your Wiki.js base URL (e.g., `https://wiki.example.com`)
   - `WIKIJS_API_KEY`: Your API token
   - `GEMINI_API_KEY`: Your Google Gemini API key (for content analysis)

2. Command line options (these override any environment variables):
   - `--url`: Your Wiki.js base URL
   - `--token`: Your API token
   - `--gemini-key`: Your Gemini API key

## Usage

The exporter provides several commands for different operations:

### Testing Connection

To test your connection to the Wiki.js API:

```bash
wikijs test --url https://your-wiki.example.com --token your_api_token
```

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
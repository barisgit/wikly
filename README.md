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

To see which Gemini models are available for use with the analyze command:

```bash
wikijs list-models
```

This will show all available Gemini models that you can use with the `--model` option.

#### Style Guide Format

The style guide should be a Markdown file containing content guidelines. An example is provided in `style_guide_example.md`.

## Getting an API Token

To use this tool, you'll need to generate an API token from your Wiki.js instance:

1. Log in to your Wiki.js instance as an administrator
2. Go to Administration > API Access
3. Click "Create New API Key"
4. Enter a name for the token (e.g., "Wiki Exporter")
5. Set the appropriate permissions (only read permissions are needed)
6. Copy the generated token and use it with the tool

For content analysis, you'll also need a Google Gemini API key:

1. Visit [Google AI Studio](https://makersuite.google.com/)
2. Sign up or log in to your Google account
3. Navigate to the API keys section
4. Create a new API key
5. Copy the key and add it to your `.env` file or use the `--gemini-key` option

## Security Considerations

- Store your API token securely
- Do not commit the `.env` file to version control
- Use an API token with the minimal required permissions (read-only)

## Output Formats

### JSON

The JSON format includes all page data in a single file:

- Page metadata (ID, title, path, tags, etc.)
- Content (both raw and rendered)
- Author information
- Creation and update timestamps

### Markdown

When exporting as Markdown:

- Each page is saved as a separate `.md` file
- Files are organized in directories matching the original wiki structure
- Metadata is included as YAML front matter
- Raw Markdown content is preserved as-is

### HTML

When exporting as HTML:

- Each page is saved as a separate `.html` file
- Files are organized in directories matching the original wiki structure
- Basic styling is included for readability
- Rendered HTML content maintains formatting and links
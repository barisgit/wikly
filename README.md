# Wiki.js Exporter

A command-line tool to export content from a Wiki.js instance using the GraphQL API. This is a **read-only** tool that will not make any changes to your Wiki.js content.

## Features

- Export pages with metadata and content from Wiki.js
- Multiple output formats (JSON, Markdown, HTML)
- Easy to use command-line interface
- Support for environment variables and configuration files
- Read-only operation (won't modify your wiki)
- Export content with original paths and hierarchy

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

2. Command line options (these override any environment variables):
   - `--url`: Your Wiki.js base URL
   - `--token`: Your API token

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

#### Additional Options

- `--delay`: Set delay between requests to avoid overwhelming the server (in seconds)
- `--debug`: Enable detailed debug output
- `--help`: Show help for any command

## Getting an API Token

To use this tool, you'll need to generate an API token from your Wiki.js instance:

1. Log in to your Wiki.js instance as an administrator
2. Go to Administration > API Access
3. Click "Create New API Key"
4. Enter a name for the token (e.g., "Wiki Exporter")
5. Set the appropriate permissions (only read permissions are needed)
6. Copy the generated token and use it with the tool

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
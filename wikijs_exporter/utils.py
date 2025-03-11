"""
Utility functions for Wiki.js exporter.
"""

import os
import json
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

def load_env_variables():
    """
    Load environment variables from .env file.
    
    Returns:
        Tuple of (base_url, api_token)
    """
    # Try to load from .env file
    load_dotenv()
    
    # Get variables
    base_url = os.getenv("WIKIJS_HOST")
    api_token = os.getenv("WIKIJS_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    return base_url, api_token, gemini_api_key

def save_pages_to_file(pages: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save the list of pages to a JSON file.
    
    Args:
        pages: List of pages to save
        output_file: Path to the output file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(pages, f, indent=2, ensure_ascii=False)
        print(f"✓ Pages saved to {output_file}")
    except Exception as e:
        print(f"Error saving pages to file: {str(e)}")
        sys.exit(1)

def save_pages_to_markdown(pages: List[Dict[str, Any]], output_dir: str) -> None:
    """
    Save the pages as individual Markdown files.
    
    Args:
        pages: List of pages to save
        output_dir: Directory to save the files in
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    saved_count = 0
    
    for page in pages:
        # Get the page content and metadata
        title = page.get('title', 'Untitled')
        path = page.get('path', '').strip('/')
        content = page.get('content', '')
        
        if not content:
            continue
            
        # Create subdirectories if needed
        if '/' in path:
            subdir = os.path.join(output_dir, os.path.dirname(path))
            os.makedirs(subdir, exist_ok=True)
        
        # Create a filename from the path or title
        if path:
            filename = os.path.join(output_dir, f"{path}.md")
        else:
            # Sanitize the title for use as a filename
            safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title])
            filename = os.path.join(output_dir, f"{safe_title}.md")
        
        # Add front matter with metadata
        front_matter = "---\n"
        # Explicitly add path and updatedAt at the beginning of metadata
        front_matter += f"path: {page.get('path', '')}\n"
        front_matter += f"updated: {page.get('updatedAt', '')}\n"
        
        # Add other important metadata
        for key in ['title', 'description', 'createdAt', 'author', 'tags']:
            if key == 'author' and 'authorName' in page:
                front_matter += f"author: {page['authorName']}\n"
            elif key == 'tags' and 'tags' in page and page['tags']:
                if isinstance(page['tags'], list):
                    # If tags is a list of strings
                    if all(isinstance(tag, str) for tag in page['tags']):
                        tags_str = ", ".join(page['tags'])
                        front_matter += f"tags: [{tags_str}]\n"
                    # If tags is a list of objects
                    elif all(isinstance(tag, dict) for tag in page['tags']):
                        tags_str = ", ".join(tag.get('tag', '') for tag in page['tags'] if 'tag' in tag)
                        front_matter += f"tags: [{tags_str}]\n"
            elif key in page and page[key]:
                front_matter += f"{key}: {page[key]}\n"
        front_matter += "---\n\n"
        
        # Write the file with front matter and content
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(front_matter + content)
            saved_count += 1
        except Exception as e:
            print(f"Error saving page {title} to {filename}: {str(e)}")
    
    print(f"✓ Saved {saved_count} pages as Markdown files in {output_dir}")

def save_pages_to_html(pages: List[Dict[str, Any]], output_dir: str) -> None:
    """
    Save the pages as individual HTML files.
    
    Args:
        pages: List of pages to save
        output_dir: Directory to save the files in
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    saved_count = 0
    
    for page in pages:
        # Get the page content and metadata
        title = page.get('title', 'Untitled')
        path = page.get('path', '').strip('/')
        html_content = page.get('render', '')
        
        if not html_content:
            continue
            
        # Create subdirectories if needed
        if '/' in path:
            subdir = os.path.join(output_dir, os.path.dirname(path))
            os.makedirs(subdir, exist_ok=True)
        
        # Create a filename from the path or title
        if path:
            filename = os.path.join(output_dir, f"{path}.html")
        else:
            # Sanitize the title for use as a filename
            safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title])
            filename = os.path.join(output_dir, f"{safe_title}.html")
        
        # Create a simple HTML document
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3, h4, h5, h6 {{ margin-top: 1.5em; margin-bottom: 0.5em; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }}
        pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 3px; overflow: auto; font-family: monospace; }}
        blockquote {{ border-left: 4px solid #dfe2e5; padding-left: 16px; margin-left: 0; color: #6a737d; }}
        img {{ max-width: 100%; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; }}
        tr:nth-child(even) {{ background-color: #f6f8fa; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {html_content}
    <hr>
    <footer>
        <p><small>Exported from Wiki.js</small></p>
    </footer>
</body>
</html>"""
        
        # Write the file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            saved_count += 1
        except Exception as e:
            print(f"Error saving page {title} to {filename}: {str(e)}")
    
    print(f"✓ Saved {saved_count} pages as HTML files in {output_dir}") 
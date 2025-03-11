"""
Utility functions for Wiki.js exporter.
"""

import os
import json
import sys
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
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

def normalize_content(content: str) -> str:
    """
    Normalize content to make hash comparison more resilient to whitespace differences.
    
    Args:
        content: Content to normalize
        
    Returns:
        Normalized content
    """
    # Replace multiple whitespace with single space
    normalized = re.sub(r'\s+', ' ', content)
    # Trim whitespace
    normalized = normalized.strip()
    return normalized

def calculate_content_hash(content: str) -> str:
    """
    Calculate a hash of the content to detect changes.
    
    Args:
        content: Content to hash
        
    Returns:
        Hash string
    """
    # Handle None or empty content
    if not content:
        return ""
        
    # Normalize content before hashing to ignore minor whitespace differences
    normalized = normalize_content(content)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def extract_content_from_file(file_content: str) -> str:
    """
    Extract actual content from a file, removing front matter for accurate hash comparison.
    
    Args:
        file_content: Content of the file (may include front matter)
        
    Returns:
        Content without front matter
    """
    # Check if file has front matter (starts with ---)
    if file_content and file_content.startswith('---'):
        # Find the end of front matter
        end_front_matter = file_content.find('---', 3)
        if end_front_matter != -1:
            # Return content after front matter
            return file_content[end_front_matter+3:].lstrip()
    
    # If no front matter found or format not recognized, return as is
    return file_content.strip() if file_content else ""

def parse_markdown_file(file_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse a markdown file, extracting front matter and content.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Tuple of (front_matter_dict, content)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if file has front matter
        if content.startswith('---'):
            end_front_matter = content.find('---', 3)
            if end_front_matter != -1:
                front_matter_text = content[3:end_front_matter].strip()
                actual_content = content[end_front_matter+3:].strip()
                
                # Parse front matter to dict
                front_matter = {}
                for line in front_matter_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        front_matter[key.strip()] = value.strip()
                
                return front_matter, actual_content
        
        # If no front matter found, return empty dict and full content
        return {}, content.strip()
    except Exception as e:
        print(f"Error parsing markdown file {file_path}: {str(e)}")
        return {}, ""

class ExportMetadata:
    """Manages metadata about previous exports for incremental operations."""
    
    def __init__(self, metadata_file: str = None, debug: bool = False):
        """
        Initialize the ExportMetadata manager.
        
        Args:
            metadata_file: File path to store metadata (default: .wikijs_export_metadata.json)
            debug: Whether to print debug information
        """
        self.metadata_file = metadata_file or os.path.join(os.getcwd(), '.wikijs_export_metadata.json')
        self.debug = debug
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file or initialize if not exists."""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if self.debug:
                        print(f"Debug: Loaded metadata from {self.metadata_file}")
                    return metadata
            else:
                if self.debug:
                    print(f"Debug: No metadata file found at {self.metadata_file}, initializing new metadata")
                return {
                    "last_export": None,
                    "pages": {}
                }
        except Exception as e:
            print(f"Warning: Could not load export metadata: {e}")
            return {
                "last_export": None,
                "pages": {}
            }
    
    def save_metadata(self, pages: List[Dict[str, Any]]) -> None:
        """
        Update and save metadata after an export.
        
        Args:
            pages: List of pages that were exported
        """
        # Update last export timestamp
        self.metadata["last_export"] = datetime.now().isoformat()
        
        # Track how many hashes were generated
        generated_hashes = 0
        preserved_hashes = 0
        empty_hashes = 0
        
        # Update page information
        for page in pages:
            page_id = str(page.get("id", ""))
            if not page_id:
                continue
                
            title = page.get("title", "Unknown")
            path = page.get("path", "")
            updated_at = page.get("updatedAt", "")
            
            # Check if we need to update this page's metadata
            has_content = "content" in page and page["content"]
            existing_entry = page_id in self.metadata["pages"]
            
            # Initialize with existing data or create new entry
            if existing_entry:
                # Start with existing data
                page_metadata = self.metadata["pages"][page_id].copy()
                # Only update these fields
                page_metadata["title"] = title
                page_metadata["path"] = path
                page_metadata["updated_at"] = updated_at
                page_metadata["export_time"] = datetime.now().isoformat()
            else:
                # Create new entry
                page_metadata = {
                    "path": path,
                    "title": title,
                    "updated_at": updated_at,
                    "hash": "",
                    "export_time": datetime.now().isoformat()
                }
            
            # Only calculate hash if we have content
            if has_content:
                content = page["content"]
                if not isinstance(content, str):
                    content = str(content)
                
                if content.strip():  # Make sure content is not just whitespace
                    content_hash = calculate_content_hash(content)
                    page_metadata["hash"] = content_hash
                    generated_hashes += 1
                    
                    if self.debug:
                        print(f"Debug: Generated hash for page {title}: {content_hash}")
                else:
                    empty_hashes += 1
                    if self.debug:
                        print(f"Warning: Empty content for page {title}")
            else:
                # If no content but hash exists, preserve it
                if existing_entry and self.metadata["pages"][page_id].get("hash"):
                    preserved_hashes += 1
                    if self.debug:
                        print(f"Debug: Preserving existing hash for page {title}: {self.metadata['pages'][page_id].get('hash')}")
            
            # Save the updated metadata for this page
            self.metadata["pages"][page_id] = page_metadata
        
        # Display hash generation statistics
        if self.debug:
            print(f"Debug: Generated {generated_hashes} hashes, preserved {preserved_hashes} hashes, {empty_hashes} pages had empty content")
        
        # Save to file
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            print(f"✓ Export metadata saved to {self.metadata_file}")
        except Exception as e:
            print(f"Warning: Could not save export metadata: {e}")
    
    def get_outdated_pages(self, pages: List[Dict[str, Any]], output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Identify pages that have been updated since the last export or have been modified locally.
        
        Args:
            pages: Current list of pages from the API
            output_dir: Directory where files were exported (optional)
            
        Returns:
            List of pages that need content updates
        """
        outdated_pages = []
        new_page_ids = []
        checked_files = {}
        
        print(f"Checking for pages that need updating...")
        if self.debug:
            print(f"Debug: Checking against {len(self.metadata['pages'])} pages in metadata")
            if output_dir:
                print(f"Debug: Checking for local changes in {output_dir}")
        
        for page in pages:
            page_id = str(page.get("id", ""))
            path = page.get("path", "")
            title = page.get("title", "Unknown")
            updated_at = page.get("updatedAt", "")
            
            # Add to new page IDs list for cleanup later
            if page_id:
                new_page_ids.append(page_id)
            
            # Reasons for updating
            update_reason = None
            
            # Check if page needs updating based on server timestamp
            if page_id not in self.metadata["pages"]:
                update_reason = "New page"
            elif self.metadata["pages"][page_id]["updated_at"] != updated_at:
                update_reason = "Updated on server"
            # Also check if stored hash is empty (might happen due to bugs)
            elif not self.metadata["pages"][page_id].get("hash"):
                update_reason = "Missing content hash"
            
            # If we've previously exported this and it's not already marked for update,
            # check if local file has been modified
            if not update_reason and page_id in self.metadata["pages"]:
                # Check for local changes in exported files (if they exist)
                safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title])
                
                if path:
                    # Determine possible file paths based on different export formats
                    possible_files = []
                    
                    # Default current directory
                    if output_dir is None:
                        # JSON output - nothing to check for local changes
                        pass
                    else:
                        # Markdown files
                        md_file = os.path.join(output_dir, f"{path}.md")
                        possible_files.append(md_file)
                        
                        # HTML files
                        html_file = os.path.join(output_dir, f"{path}.html")
                        possible_files.append(html_file)
                        
                        # Files with sanitized titles (used if path isn't available)
                        md_title_file = os.path.join(output_dir, f"{safe_title}.md")
                        html_title_file = os.path.join(output_dir, f"{safe_title}.html")
                        possible_files.extend([md_title_file, html_title_file])
                    
                    # Check all possible file locations
                    for file_path in possible_files:
                        if os.path.exists(file_path) and file_path not in checked_files:
                            checked_files[file_path] = True
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                    
                                    # Extract just the content part without front matter
                                    actual_content = extract_content_from_file(file_content)
                                    
                                    # Hash only the actual content
                                    current_hash = calculate_content_hash(actual_content)
                                    stored_hash = self.metadata["pages"][page_id].get("hash", "")
                                    
                                    if self.debug:
                                        print(f"Debug: Checking file {file_path}")
                                        print(f"  - Stored hash: {stored_hash}")
                                        print(f"  - Current hash: {current_hash}")
                                        print(f"  - Content length: {len(actual_content)}")
                                    
                                    if stored_hash and current_hash != stored_hash:
                                        update_reason = f"Local changes detected in {file_path}"
                                        if self.debug:
                                            print(f"Debug: Content hash mismatch for {file_path}")
                                        break
                            except Exception as e:
                                # If we can't read the file, assume it needs updating
                                if self.debug:
                                    print(f"Warning: Could not check file {file_path} for changes: {e}")
            
            if update_reason:
                outdated_pages.append(page)
                if self.debug or len(outdated_pages) <= 5:  # Limit output for large exports
                    print(f"  • {title} ({path}) - {update_reason}")
                elif len(outdated_pages) == 6:
                    print(f"  • ... and more (use --debug for full details)")
        
        # Clean up deleted pages
        for page_id in list(self.metadata["pages"].keys()):
            if page_id not in new_page_ids:
                if self.debug:
                    page_info = self.metadata["pages"][page_id]
                    print(f"Debug: Removing deleted page from metadata: {page_info['title']} ({page_info['path']})")
                del self.metadata["pages"][page_id]
        
        return outdated_pages
    
    def get_last_export_time(self) -> Optional[str]:
        """Get the timestamp of the last export, if available."""
        return self.metadata.get("last_export")

    def reset_hashes(self) -> None:
        """Reset all content hashes in the metadata."""
        if self.debug:
            print(f"Debug: Resetting all content hashes in metadata")
            
        # Reset all hashes to empty strings
        for page_id in self.metadata["pages"]:
            self.metadata["pages"][page_id]["hash"] = ""
            
        if self.debug:
            print(f"Debug: Reset {len(self.metadata['pages'])} hashes")

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
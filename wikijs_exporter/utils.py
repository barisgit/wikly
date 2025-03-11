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
from dataclasses import dataclass
import click

def load_env_variables():
    """
    Load environment variables from .env file.
    
    Returns:
        Tuple of (base_url, api_token, gemini_api_key)
    """
    # First, check if the .env file exists in the current directory and print debug info
    current_dir = os.getcwd()
    env_file = os.path.join(current_dir, '.env')
    
    if os.path.exists(env_file):
        click.echo(f"Found .env file at: {env_file}")
        try:
            with open(env_file, 'r') as f:
                env_contents = f.read()
                # Print first line of content (safely, without exposing full secrets)
                lines = env_contents.strip().split('\n')
                click.echo(f".env file contains {len(lines)} line(s)")
                for i, line in enumerate(lines):
                    if '=' in line and not line.startswith('#'):
                        var_name = line.split('=')[0]
                        click.echo(f"  Line {i+1}: {var_name}=***")
        except Exception as e:
            click.echo(f"Warning: Found .env file but couldn't read it: {e}")
    else:
        click.echo(f"No .env file found in current directory: {current_dir}")
    
    # Try to load from .env file in current directory
    click.echo("Attempting to load environment variables from current directory")
    load_dotenv(dotenv_path=env_file, override=True)
    
    # Check if keys were loaded
    if any([os.getenv("WIKIJS_HOST"), os.getenv("WIKIJS_API_KEY"), os.getenv("GEMINI_API_KEY")]):
        click.echo("✓ Successfully loaded some environment variables from .env file")
    else:
        click.echo("No environment variables were loaded from .env file")
        
        # Also try looking in the parent directory if env vars not found
        parent_env = os.path.join(os.path.dirname(os.getcwd()), '.env')
        if os.path.exists(parent_env):
            click.echo(f"Trying parent directory .env file: {parent_env}")
            load_dotenv(dotenv_path=parent_env, override=True)
            click.echo(f"✓ Loaded environment variables from {parent_env}")
        
        # Also try looking for .env in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_env = os.path.join(script_dir, '.env')
        if os.path.exists(script_env):
            click.echo(f"Trying script directory .env file: {script_env}")
            load_dotenv(dotenv_path=script_env, override=True)
            click.echo(f"✓ Loaded environment variables from {script_env}")
    
    # Get variables
    base_url = os.getenv("WIKIJS_HOST")
    api_token = os.getenv("WIKIJS_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    # Debug info
    found_vars = []
    if base_url:
        found_vars.append("WIKIJS_HOST")
    if api_token:
        found_vars.append("WIKIJS_API_KEY")
    if gemini_api_key:
        found_vars.append("GEMINI_API_KEY")
    
    if found_vars:
        click.echo(f"Found environment variables: {', '.join(found_vars)}")
    else:
        click.echo("WARNING: No environment variables were found")
    
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

class AnalysisMetadata:
    """Manages metadata about previous analyses for incremental operations."""
    
    def __init__(self, metadata_file: str = None, debug: bool = False):
        """
        Initialize the AnalysisMetadata manager.
        
        Args:
            metadata_file: File path to store metadata (default: .wikijs_analysis_metadata.json)
            debug: Whether to print debug information
        """
        self.metadata_file = metadata_file or os.path.join(os.getcwd(), '.wikijs_analysis_metadata.json')
        self.debug = debug
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file or initialize if not exists."""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if self.debug:
                        print(f"Debug: Loaded analysis metadata from {self.metadata_file}")
                    return metadata
            else:
                if self.debug:
                    print(f"Debug: No analysis metadata file found at {self.metadata_file}, initializing new metadata")
                return {
                    "last_analysis": None,
                    "pages": {}
                }
        except Exception as e:
            print(f"Warning: Could not load analysis metadata: {e}")
            return {
                "last_analysis": None,
                "pages": {}
            }
    
    def save_metadata(self, pages: List[Dict[str, Any]]) -> None:
        """
        Update and save metadata after an analysis.
        
        Args:
            pages: List of pages that were analyzed
        """
        # Update last analysis timestamp
        self.metadata["last_analysis"] = datetime.now().isoformat()
        
        # Update page information
        for page in pages:
            path = page.get("path", "")
            if not path:
                continue
                
            title = page.get("title", "Unknown")
            content = page.get("content", "")
            
            # Calculate content hash
            content_hash = calculate_content_hash(content) if content else ""
            
            # Create or update page metadata
            page_metadata = {
                "path": path,
                "title": title,
                "content_hash": content_hash,
                "analysis_time": datetime.now().isoformat()
            }
            
            # Store analysis results if available
            if "analysis" in page and page["analysis"]:
                page_metadata["has_analysis"] = True
                
                # Store summary for quick reference
                if isinstance(page["analysis"], dict):
                    analysis_data = page["analysis"].get("analysis", {})
                    if isinstance(analysis_data, dict):
                        score = analysis_data.get("compliance_score")
                        if score is not None:
                            page_metadata["compliance_score"] = score
                            
                        discrepancies = analysis_data.get("discrepancies", [])
                        page_metadata["issue_count"] = len(discrepancies)
            else:
                page_metadata["has_analysis"] = False
            
            # Save the metadata for this page
            self.metadata["pages"][path] = page_metadata
        
        # Save to file
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            print(f"✓ Analysis metadata saved to {self.metadata_file}")
        except Exception as e:
            print(f"Warning: Could not save analysis metadata: {e}")
    
    def get_outdated_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify pages that need to be analyzed because they have changed since the last analysis.
        
        Args:
            pages: Current list of pages to analyze
            
        Returns:
            List of pages that need analysis updates
        """
        outdated_pages = []
        
        print(f"Checking for pages that need analyzing...")
        if self.debug:
            print(f"Debug: Checking against {len(self.metadata['pages'])} pages in metadata")
        
        for page in pages:
            path = page.get("path", "")
            title = page.get("title", "Unknown")
            content = page.get("content", "")
            
            # Reasons for updating
            update_reason = None
            
            # Skip pages with no content
            if not content:
                if self.debug:
                    print(f"Debug: Skipping {title} ({path}) - No content")
                continue
            
            # Calculate current content hash
            current_hash = calculate_content_hash(content)
            
            # Check if page needs analyzing
            if path not in self.metadata["pages"]:
                update_reason = "Never analyzed"
            elif not self.metadata["pages"][path].get("has_analysis", False):
                update_reason = "Previous analysis failed or not completed"
            elif not self.metadata["pages"][path].get("content_hash"):
                update_reason = "Missing content hash"
            elif self.metadata["pages"][path].get("content_hash") != current_hash:
                update_reason = "Content changed since last analysis"
            
            if update_reason:
                outdated_pages.append(page)
                if self.debug or len(outdated_pages) <= 5:  # Limit output for large analyses
                    print(f"  • {title} ({path}) - {update_reason}")
                elif len(outdated_pages) == 6:
                    print(f"  • ... and more (use --debug for full details)")
            elif self.debug:
                print(f"Debug: Skipping {title} ({path}) - No changes since last analysis")
        
        # Clean up deleted pages
        current_paths = {page.get("path", "") for page in pages if page.get("path", "")}
        for path in list(self.metadata["pages"].keys()):
            if path not in current_paths:
                if self.debug:
                    page_info = self.metadata["pages"][path]
                    print(f"Debug: Removing deleted page from metadata: {page_info['title']} ({path})")
                del self.metadata["pages"][path]
        
        return outdated_pages
    
    def get_last_analysis_time(self) -> Optional[str]:
        """Get the timestamp of the last analysis, if available."""
        return self.metadata.get("last_analysis")

    def reset_content_hashes(self) -> None:
        """Reset all content hashes in the metadata to force reanalysis."""
        if self.debug:
            print(f"Debug: Resetting all content hashes in analysis metadata")
            
        # Reset all hashes to empty strings
        for path in self.metadata["pages"]:
            self.metadata["pages"][path]["content_hash"] = ""
            
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

def load_pages_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load pages from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of pages
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading pages from file: {str(e)}")
        return []

def load_pages_from_markdown(directory_path: str) -> List[Dict[str, Any]]:
    """
    Load pages from a directory of Markdown files.
    
    Args:
        directory_path: Path to the directory containing Markdown files
        
    Returns:
        List of pages with metadata and content
    """
    pages = []
    path = Path(directory_path)
    
    if not path.exists() or not path.is_dir():
        print(f"Error: {directory_path} is not a valid directory")
        return []
    
    # Find all markdown files recursively
    markdown_files = list(path.glob("**/*.md"))
    
    for file_path in markdown_files:
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from frontmatter if present
            title = file_path.stem  # Default to filename
            page_path = str(file_path.relative_to(path))
            updated_at = ""
            
            # Try to extract frontmatter
            frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                # Extract title if present
                title_match = re.search(r'title:\s*(.*)', frontmatter)
                if title_match:
                    title = title_match.group(1).strip()
                
                # Extract path if present
                path_match = re.search(r'path:\s*(.*)', frontmatter)
                if path_match:
                    page_path = path_match.group(1).strip()
                
                # Extract updated_at if present
                updated_match = re.search(r'updated(?:_at)?:\s*(.*)', frontmatter)
                if updated_match:
                    updated_at = updated_match.group(1).strip()
            
            # Create page object
            page = {
                "id": str(file_path),
                "path": page_path,
                "title": title,
                "content": content,
                "updatedAt": updated_at
            }
            
            pages.append(page)
            
        except Exception as e:
            print(f"Error loading page from {file_path}: {str(e)}")
    
    return pages 

def generate_sitemap(pages: List[Dict[str, Any]], max_chars: int = 10000, detail_level: int = 2) -> str:
    """
    Generate a sitemap visualization from a list of wiki pages with adaptive detail based on size constraints.
    
    Args:
        pages: List of page objects with 'path' and 'title' keys
        max_chars: Maximum number of characters to include in the sitemap (default: 10000)
        detail_level: Level of detail to include (0=structure only, 1=basic info, 2=full details)
        
    Returns:
        A string representation of the sitemap in tree format, limited to max_chars
    """
    # Build a tree structure from the page paths
    tree = {}
    
    # Sort pages by path to ensure parent directories come before children
    sorted_pages = sorted(pages, key=lambda x: x.get('path', ''))
    
    # Build the tree
    for page in sorted_pages:
        path = page.get('path', '')
        if not path or path.startswith('http'):  # Skip empty paths or URLs
            continue
            
        # Split the path into segments
        segments = path.split('/')
        
        # Start at the root of the tree
        current = tree
        
        # Build the tree structure
        for i, segment in enumerate(segments):
            if segment not in current:
                current[segment] = {
                    'children': {},
                    'segment': segment,
                    'is_page': False,
                    'is_folder': False,
                    'depth': i + 1
                }
            
            # If this is the last segment, mark it as a page and store metadata
            if i == len(segments) - 1:
                current[segment]['is_page'] = True
                current[segment]['title'] = page.get('title', 'Untitled')
                current[segment]['word_count'] = len(page.get('content', '').split()) if page.get('content') else 0
                current[segment]['updated'] = page.get('updatedAt', 'unknown date')
                current[segment]['description'] = page.get('description', '')
                current[segment]['path'] = path
                
                # Store the actual content for potential outline extraction if needed
                if page.get('content') and detail_level >= 3:
                    current[segment]['content'] = page.get('content', '')
            
            # Check if this is a folder (has children)
            for p in sorted_pages:
                p_path = p.get('path', '')
                if p_path and p_path != path and p_path.startswith(path + '/'):
                    current[segment]['is_folder'] = True
                    break
            
            # Move to the next level of the tree
            current = current[segment]['children']
    
    # Helper functions
    def format_date(date_str):
        """Format date string nicely if possible"""
        if date_str and date_str != 'unknown date':
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return date_obj.strftime('%Y-%m-%d')
            except Exception:
                pass
        return date_str
    
    def extract_outline(content, max_lines=5):
        """Extract a simple outline from content (first few lines and headings)"""
        if not content:
            return []
            
        lines = content.split('\n')
        outline = []
        
        # Extract first line (often a summary or intro)
        if lines and not lines[0].startswith('#'):
            first_line = lines[0].strip()
            if first_line and len(first_line) > 5:
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
                outline.append(first_line)
        
        # Extract headings
        headings = [line for line in lines if line.strip().startswith('#') and len(line.strip()) > 2]
        for h in headings[:max_lines-1]:  # Limit headings
            heading = h.strip()
            if len(heading) > 80:
                heading = heading[:77] + "..."
            outline.append(heading)
            
        if len(headings) > max_lines-1:
            outline.append("... and more headings")
            
        return outline
    
    # Build the complete sitemap structure (as a list of dicts for easy manipulation)
    sitemap_structure = []
    
    def build_structure(node_dict, prefix='', path_segments=None, is_last=True):
        """Recursively build structured sitemap from tree"""
        if path_segments is None:
            path_segments = []
        
        for i, (key, node) in enumerate(sorted(node_dict.items())):
            current_is_last = (i == len(node_dict) - 1)
            
            # Create structure entry
            entry = {
                'segment': key,
                'prefix': prefix,
                'is_last': current_is_last,
                'depth': node.get('depth', len(path_segments)),
                'is_page': node.get('is_page', False),
                'is_folder': node.get('is_folder', False),
                'path': node.get('path', '/'.join(path_segments + [key])),
                'metadata': {}
            }
            
            if node.get('is_page', False):
                entry['title'] = node.get('title', key)
                entry['metadata'] = {
                    'word_count': node.get('word_count', 0),
                    'updated': node.get('updated', 'unknown date'),
                    'description': node.get('description', '')
                }
                
                # Add outline if content is available and detail level warrants it
                if 'content' in node and detail_level >= 3:
                    entry['outline'] = extract_outline(node.get('content', ''))
                
                # Determine page type
                if node.get('is_folder', False):
                    entry['page_type'] = 'folder page'
                else:
                    entry['page_type'] = 'content page'
            
            # Add to structure
            sitemap_structure.append(entry)
            
            # Process children
            if 'children' in node and node['children']:
                new_prefix = prefix + ('    ' if current_is_last else '│   ')
                new_path_segments = path_segments + [key]
                build_structure(node['children'], new_prefix, new_path_segments, current_is_last)
    
    # Build the complete structure
    build_structure(tree)
    
    # Now render the sitemap with progressive detail levels, respecting the character limit
    rendered_lines = []
    used_chars = 0
    
    # First, calculate the max depth in the sitemap structure
    max_depth_in_structure = max(entry['depth'] for entry in sitemap_structure) if sitemap_structure else 0
    
    # Tiers of importance for rendering:
    # 1. Complete structure with minimum detail to show hierarchy
    # 2. Add basic metadata (word count, dates)
    # 3. Add descriptions
    # 4. Add content outlines
    
    # Render line function (returns text and character count)
    def render_entry(entry, tier):
        """Render a single sitemap entry with detail based on tier level"""
        line = ""
        
        # Basic structure (always show)
        line += f"{entry['prefix']}{'└── ' if entry['is_last'] else '├── '}{entry['segment']}"
        
        if entry['is_page']:
            # Add page type indicator
            line += f" ({entry['page_type']}: {entry['title']})"
            
            # Tier 1+: Add basic metadata
            if tier >= 1 and 'metadata' in entry:
                word_count = entry['metadata'].get('word_count', 0)
                updated = format_date(entry['metadata'].get('updated', ''))
                line += f" [{word_count} words, updated: {updated}]"
            
            # Tier 2+: Add description
            if tier >= 2 and 'metadata' in entry and entry['metadata'].get('description'):
                description = entry['metadata'].get('description', '')
                if description and len(description) > 5:
                    if len(description) > 80:
                        description = description[:77] + "..."
                    line += f"\n{entry['prefix']}{'    ' if entry['is_last'] else '│   '} → {description}"
            
            # Tier 3+: Add outline
            if tier >= 3 and 'outline' in entry and entry['outline']:
                indent = entry['prefix'] + ('    ' if entry['is_last'] else '│   ')
                for outline_line in entry['outline']:
                    line += f"\n{indent} | {outline_line}"
        
        return line
    
    # Strategy: Start with complete tree at minimum detail, then add detail progressively
    for tier in range(4):  # 0-3 detail tiers
        # Skip higher tiers if detail_level doesn't warrant them
        if tier > detail_level:
            continue
            
        # Calculate lines we can add at this tier
        tier_lines = []
        
        # First tier (0) - render all entries with minimal detail
        if tier == 0:
            for entry in sitemap_structure:
                line = render_entry(entry, tier)
                tier_lines.append((line, len(line)))
        else:
            # Higher tiers - add more detail to entries we already have
            for idx, entry in enumerate(sitemap_structure):
                # Skip entries that have no page info (they won't get more detail)
                if not entry['is_page']:
                    continue
                
                line = render_entry(entry, tier)
                # Check if we already have an older version of this line
                if idx < len(rendered_lines):
                    # Calculate what will be added to existing entry
                    old_line_len = len(rendered_lines[idx])
                    new_chars = len(line) - old_line_len
                    tier_lines.append((line, new_chars))
                else:
                    tier_lines.append((line, len(line)))
        
        # Try to add lines from this tier, respecting character limit
        # Sort by depth for breadth-first display within tier
        sorted_tier_lines = sorted(enumerate(tier_lines), key=lambda x: sitemap_structure[x[0]]['depth'])
        
        for idx, (line, char_count) in sorted_tier_lines:
            # Check if we can add this line
            if used_chars + char_count <= max_chars:
                if idx < len(rendered_lines):
                    # Replace existing entry
                    used_chars = used_chars - len(rendered_lines[idx]) + len(line)
                    rendered_lines[idx] = line
                else:
                    # Add new entry
                    rendered_lines.append(line)
                    used_chars += char_count
            else:
                # We've reached the limit, stop here
                break
        
        # If we can't fit everything in this tier, stop adding more
        if used_chars >= max_chars * 0.95:
            break
    
    # If we couldn't fit everything, add a truncation message
    if used_chars >= max_chars * 0.95:
        total_entries = len(sitemap_structure)
        rendered_entries = len(rendered_lines)
        remaining = total_entries - rendered_entries
        
        if remaining > 0:
            truncation_msg = f"\n... {remaining} more entries not shown due to character limit ..."
            if used_chars + len(truncation_msg) <= max_chars:
                rendered_lines.append(truncation_msg)
    
    # Add summary information if we have space left
    if used_chars < max_chars * 0.95:
        total_pages = len(sorted_pages)
        folder_pages = sum(1 for entry in sitemap_structure if entry.get('is_page') and entry.get('is_folder'))
        content_pages = sum(1 for entry in sitemap_structure if entry.get('is_page') and not entry.get('is_folder'))
        total_words = sum(entry.get('metadata', {}).get('word_count', 0) for entry in sitemap_structure if entry.get('is_page'))
        avg_length = total_words // max(1, content_pages) if content_pages > 0 else 0
        
        summary_lines = [
            "\nSITEMAP SUMMARY:",
            f"Total pages: {total_pages} ({folder_pages} folder pages, {content_pages} content pages)",
            f"Total word count: {total_words} words",
            f"Average page length: {avg_length} words per content page",
            f"Character count: {used_chars:,} of {max_chars:,} ({(used_chars/max_chars)*100:.1f}% of limit)"
        ]
        
        # Check if adding the summary would exceed the limit
        summary_text = "\n".join(summary_lines)
        if used_chars + len(summary_text) < max_chars:
            rendered_lines.extend(summary_lines)
    
    return "\n".join(rendered_lines)

def get_page_type(page_path: str, pages: List[Dict[str, Any]]) -> str:
    """
    Determine if a page is likely a folder page or content page based on the sitemap.
    
    Args:
        page_path: Path of the page to check
        pages: List of all pages
        
    Returns:
        'folder_page' or 'content_page'
    """
    # Check if there are any subpages
    has_children = any(p.get('path', '').startswith(page_path + '/') for p in pages if p.get('path') != page_path)
    
    if has_children:
        return 'folder_page'
    else:
        return 'content_page' 
"""
API interaction module for Wiki.js GraphQL API.
"""

import time
import requests
from typing import List, Dict, Any, Optional

class WikiJSAPI:
    """Client for interacting with the Wiki.js GraphQL API."""
    
    def __init__(self, base_url: str, api_token: str, debug: bool = False):
        """
        Initialize the WikiJSAPI client.
        
        Args:
            base_url: Base URL of the Wiki.js instance
            api_token: API token for authentication
            debug: Whether to print debug information
        """
        # Ensure the base URL doesn't end with a slash
        self.base_url = base_url
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
            
        self.api_token = api_token
        self.debug = debug
        self.graphql_endpoint = f"{self.base_url}/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if self.debug:
            print(f"Debug: GraphQL endpoint: {self.graphql_endpoint}")
            print(f"Debug: Headers: {self.headers}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to the Wiki.js GraphQL API.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        test_query = {
            "query": """
            {
                pages {
                    list(limit: 1) {
                        id
                        title
                    }
                }
            }
            """
        }
        
        try:
            if self.debug:
                print(f"Debug: Sending test query: {test_query}")
                
            response = requests.post(self.graphql_endpoint, json=test_query, headers=self.headers)
            
            if self.debug:
                print(f"Debug: Response status code: {response.status_code}")
                print(f"Debug: Response content: {response.text[:500]}...")
                
            response.raise_for_status()
            
            data = response.json()
            if "errors" in data:
                error_msg = data["errors"][0]["message"]
                print(f"GraphQL Error: {error_msg}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error making test request: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text[:1000]}")
            return False
    
    def fetch_pages(self) -> List[Dict[str, Any]]:
        """
        Fetch list of all pages from Wiki.js.
        
        Returns:
            List of all pages with their metadata (no content)
        """
        all_pages = []
        
        print(f"Fetching pages from {self.base_url}...")
        
        # Test connection first
        if not self.test_connection():
            print("Connection test failed. Cannot fetch pages.")
            return []
            
        print("✓ Connection test successful")
        
        # Fetch all pages with a single query using a high limit
        query = {
            "query": """
            {
                pages {
                    list(limit: 10000, orderBy: TITLE) {
                        id
                        path
                        locale
                        title
                        description
                        contentType
                        isPublished
                        isPrivate
                        privateNS
                        createdAt
                        updatedAt
                        tags
                    }
                }
            }
            """
        }
        
        try:
            if self.debug:
                print(f"Debug: Sending query: {query}")
                
            response = requests.post(self.graphql_endpoint, json=query, headers=self.headers)
            
            if self.debug:
                print(f"Debug: Response status code: {response.status_code}")
                if response.status_code != 200:
                    print(f"Debug: Response content: {response.text[:500]}...")
                    
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors in the response
            if "errors" in data:
                error_msg = data["errors"][0]["message"]
                print(f"GraphQL Error: {error_msg}")
                if self.debug:
                    print(f"Full GraphQL error response: {data['errors']}")
                return []
            
            # Get the list of pages from the response
            pages = data.get("data", {}).get("pages", {}).get("list", [])
            
            # Add the pages to our list
            all_pages.extend(pages)
            print(f"✓ Successfully fetched metadata for {len(all_pages)} pages")
            
        except Exception as e:
            print(f"Error fetching pages: {str(e)}")
            return []
        
        return all_pages
    
    def fetch_page_content(self, page_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch the full content of a single page.
        
        Args:
            page_id: ID of the page to fetch
            
        Returns:
            Dictionary with the page's full content and metadata, or None if an error occurred
        """
        # Build the GraphQL query to fetch a single page by ID
        # Note: We exclude the toc field which can cause errors
        query = {
            "query": """
            query ($id: Int!) {
                pages {
                    single(id: $id) {
                        id
                        path
                        hash
                        title
                        description
                        isPrivate
                        isPublished
                        privateNS
                        publishStartDate
                        publishEndDate
                        tags {
                            id
                            tag
                            title
                        }
                        content
                        render
                        contentType
                        createdAt
                        updatedAt
                        editor
                        locale
                        authorId
                        authorName
                        authorEmail
                        creatorId
                        creatorName
                        creatorEmail
                    }
                }
            }
            """,
            "variables": {
                "id": page_id
            }
        }
        
        try:
            # Make the request to the GraphQL API
            if self.debug:
                print(f"Debug: Fetching content for page ID {page_id}")
                
            response = requests.post(self.graphql_endpoint, json=query, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors in the response
            if "errors" in data:
                error_msg = data["errors"][0]["message"]
                print(f"GraphQL Error fetching page {page_id}: {error_msg}")
                return None
            
            # Get the page from the response
            page = data.get("data", {}).get("pages", {}).get("single", {})
            
            if not page:
                print(f"Warning: No content returned for page ID {page_id}")
                return None
                
            return page
            
        except Exception as e:
            print(f"Error fetching content for page {page_id}: {str(e)}")
            return None
    
    def fetch_all_pages_with_content(self, delay: float = 0.1) -> List[Dict[str, Any]]:
        """
        Fetch all pages and their content.
        
        Args:
            delay: Delay in seconds between requests to avoid rate limiting
            
        Returns:
            List of all pages with their full content
        """
        # First, get the list of all pages
        pages = self.fetch_pages()
        
        if not pages:
            print("No pages found to fetch content for.")
            return []
        
        print(f"Fetching content for {len(pages)} pages...")
        
        # Fetch the content for each page
        full_pages = []
        successful = 0
        failed = 0
        
        for i, page in enumerate(pages):
            page_id = page.get("id")
            title = page.get("title", "Unknown")
            
            print(f"[{i+1}/{len(pages)}] Fetching content for '{title}' (ID: {page_id})...", end="", flush=True)
            
            # Fetch the content
            full_page = self.fetch_page_content(page_id)
            
            if full_page:
                full_pages.append(full_page)
                print(" ✓")
                successful += 1
            else:
                # If we couldn't get the full page, at least keep the metadata
                print(" ✗")
                full_pages.append(page)
                failed += 1
            
            # Add a delay to avoid overwhelming the server
            if i < len(pages) - 1:
                time.sleep(delay)
        
        print(f"\nContent fetching complete. Successfully fetched {successful} pages, failed to fetch {failed} pages.")
        
        return full_pages 
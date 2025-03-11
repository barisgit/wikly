"""
Module for analyzing Wiki.js content using the Gemini API.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
import requests

class ContentAnalyzer:
    """Client for analyzing Wiki.js content using the Gemini API."""
    
    def __init__(self, api_key: str, debug: bool = False):
        """
        Initialize the ContentAnalyzer.
        
        Args:
            api_key: Gemini API key
            debug: Whether to print debug information
        """
        self.api_key = api_key
        self.debug = debug
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        if self.debug:
            print(f"Debug: Initialized ContentAnalyzer with API key: {api_key[:4]}...{api_key[-4:]}")
    
    def analyze_pages(self, pages: List[Dict[str, Any]], style_guide: str = None, ai_guide: str = None) -> List[Dict[str, Any]]:
        """
        Analyze a list of pages from Wiki.js.
        
        Args:
            pages: List of pages with content
            style_guide: Style guide content (if None, uses default)
            ai_guide: AI-specific instructions (if None, ignores)
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i, page in enumerate(pages):
            print(f"[{i+1}/{len(pages)}] Analyzing '{page.get('title', 'Untitled page')}'...")
            
            # Extract content based on type in the data
            content = page.get('content', '')
            if not content:
                results.append({
                    "path": page.get("path", "unknown"),
                    "title": page.get("title", "Untitled"),
                    "analysis": {
                        "success": False,
                        "message": "No content found in page"
                    }
                })
                continue
            
            # Analyze the content
            analysis = self._analyze_content(content, style_guide, ai_guide)
            
            # Create result
            result = {
                "path": page.get("path", "unknown"),
                "title": page.get("title", "Untitled"),
                "analysis": analysis
            }
            
            results.append(result)
            
            # Add delay between API calls to prevent rate limiting
            if i < len(pages) - 1:
                time.sleep(1.0)
        
        return results
    
    def _analyze_content(self, content: str, style_guide: str = None, ai_guide: str = None) -> Dict[str, Any]:
        """
        Analyze content using the Gemini API.
        
        Args:
            content: The content to analyze
            style_guide: Style guide content (if None, uses default)
            ai_guide: AI-specific instructions (if None, ignores)
            
        Returns:
            Dictionary with analysis results
        """
        # Create prompt for Gemini
        prompt = self._create_analysis_prompt(content, style_guide, ai_guide)
        
        # Call Gemini API
        response = self._call_gemini_api(prompt)
        
        if not response:
            return {
                "success": False,
                "message": "Failed to get response from Gemini API"
            }
        
        # Parse response
        try:
            analysis = self._parse_gemini_response(response)
            return {
                "success": True,
                "analysis": analysis
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error parsing response: {str(e)}"
            }
    
    def _create_analysis_prompt(self, content: str, style_guide: str = None, ai_guide: str = None) -> str:
        """
        Create a prompt for Gemini to analyze content.
        
        Args:
            content: The content to analyze
            style_guide: Style guide content (if None, uses default)
            ai_guide: AI-specific instructions (if None, ignores)
            
        Returns:
            Prompt string
        """
        # Use provided style guide or default
        if not style_guide:
            style_guide = """
# Wiki Content Style Guide

## General Guidelines
- Use consistent terminology throughout all pages
- Use title case for headings
- Use sentence case for all other text
- Tables should have clear headers and consistent formatting
- Code blocks should be properly formatted with language specified
- Use numbered lists for sequential steps
- Use bullet points for non-sequential items
- Keep paragraphs concise and focused
- Include a clear introduction at the beginning of each page
- Provide a conclusion or summary where appropriate

## Markdown Formatting
- Use the appropriate heading levels (# for main title, ## for sections)
- Use *italics* for emphasis, not all caps
- Use **bold** for important terms or warnings
- Use `code` for inline code references
- Use code blocks with language specifier for multi-line code

## Technical Content
- Define acronyms on first use
- Link to related pages when referencing other topics
- Include examples where helpful
- Tables should be used to present structured data
- Images should have clear captions
- Diagrams should be properly labeled
- Procedures should be numbered and have a clear goal stated

## Language and Tone
- Use active voice where possible
- Be concise and direct
- Avoid jargon unless necessary for the topic
- Maintain professional tone
- Use present tense where possible
- Use second person ("you") when addressing the reader
"""

        # Start building the prompt
        prompt = f"""
You are a content analyzer for a technical wiki. Your task is to analyze the content below and identify any style, formatting, or consistency issues based on the provided style guide.

# STYLE GUIDE:
{style_guide}
"""

        # Add AI guide if provided
        if ai_guide:
            prompt += f"""
# AI-SPECIFIC INSTRUCTIONS:
{ai_guide}
"""

        # Continue with content and instructions
        prompt += f"""
# CONTENT TO ANALYZE:
{content}

# ANALYSIS INSTRUCTIONS:
1. Identify any discrepancies with the style guide
2. For each discrepancy, provide:
   - A brief description of the issue
   - The specific section or line where it occurs
   - A suggested correction
   - A severity level (low, medium, high)

Format your response as a JSON object with the following structure:
{{
    "summary": "Brief overall assessment",
    "discrepancies": [
        {{
            "issue": "Description of the issue",
            "location": "Section or line reference",
            "severity": "low|medium|high",
            "suggestion": "Suggested correction"
        }}
    ],
    "compliance_score": "A value between 0-100 indicating how well the content follows the style guide"
}}

If no discrepancies are found, return an empty array for discrepancies and a compliance score of 100.
"""
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Call the Gemini API with the given prompt.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            API response or None if failed
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 8192,
            }
        }
        
        url = f"{self.api_url}?key={self.api_key}"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            return response.json()
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
    
    def _parse_gemini_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the response from the Gemini API.
        
        Args:
            response: API response
            
        Returns:
            Parsed analysis data
        """
        try:
            # Extract the text from the response
            candidates = response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts in content")
            
            text = parts[0].get("text", "")
            if not text:
                raise ValueError("No text in part")
            
            # Find the JSON part of the response
            json_start = text.find("{")
            json_end = text.rfind("}")
            
            if json_start == -1 or json_end == -1:
                raise ValueError("No JSON object found in response")
            
            json_text = text[json_start:json_end+1]
            
            # Parse the JSON
            result = json.loads(json_text)
            return result
            
        except Exception as e:
            print(f"Error parsing Gemini response: {str(e)}")
            # Return a default analysis object
            return {
                "summary": "Failed to analyze content due to an error",
                "discrepancies": [],
                "compliance_score": 0
            } 
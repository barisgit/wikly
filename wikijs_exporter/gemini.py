"""
Module for interacting with the Gemini API to analyze wiki content.
"""

import os
import time
import json
import random  # Add import for random module
from typing import Dict, List, Any, Optional, Tuple
import requests
from pathlib import Path


class GeminiAnalyzer:
    """Client for analyzing content using the Gemini API."""
    
    def __init__(self, api_key: str, debug: bool = False):
        """
        Initialize the GeminiAnalyzer.
        
        Args:
            api_key: Gemini API key
            debug: Whether to print debug information
        """
        self.api_key = api_key
        self.debug = debug
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        if self.debug:
            print(f"Debug: Initialized GeminiAnalyzer with API key: {api_key[:4]}...{api_key[-4:]}")
            print(f"Debug: Using model URL: {self.api_url}")
    
    def analyze_content(self, content: str, style_guide: str, ai_guide: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze content against a style guide using Gemini.
        
        Args:
            content: The wiki content to analyze
            style_guide: The style guide to compare against
            ai_guide: Optional AI-specific guidance
            
        Returns:
            Dictionary with analysis results
        """
        prompt = self._create_analysis_prompt(content, style_guide, ai_guide)
        
        if self.debug:
            print(f"Debug: Sending content of length {len(content)} to Gemini API")
            
        response = self._call_gemini_api(prompt)
        
        if not response:
            return {
                "success": False,
                "message": "Failed to get response from Gemini API",
                "discrepancies": []
            }
            
        # Extract and process the analysis result
        analysis = self._parse_gemini_response(response)
        
        return analysis
    
    def _create_analysis_prompt(self, content: str, style_guide: str, ai_guide: Optional[str] = None) -> str:
        """
        Create a prompt for Gemini to analyze content against a style guide.
        
        Args:
            content: The content to analyze
            style_guide: The style guide to compare against
            ai_guide: Optional AI-specific guidance
            
        Returns:
            Prompt string for Gemini
        """
        prompt = f"""
You are a content consistency analyzer for a wiki. Your task is to analyze the following wiki content and identify any discrepancies or inconsistencies with the provided style guide.

# STYLE GUIDE:
{style_guide}
"""

        # Add AI guide if provided
        if ai_guide:
            prompt += f"""
# ADDITIONAL AI GUIDANCE:
{ai_guide}
"""

        prompt += f"""
# CONTENT TO ANALYZE:
{content}

# ANALYSIS INSTRUCTIONS:
1. Identify any discrepancies between the content and the style guide
2. For each discrepancy, provide:
   - A brief description of the issue
   - The specific section or line where it occurs
   - A suggested correction

3. IMPORTANT GUIDELINES:
   - Do NOT flag HTML content as an issue - Wiki.js supports HTML content as stated in the style guide
   - Respect the guidelines for acronyms (like BLE, PCB, API) which should maintain their standard capitalization in titles and headings
   - Only flag issues that are explicitly mentioned in the style guide

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
            prompt: The prompt to send to Gemini
            
        Returns:
            Dictionary with the API response, or None if the request failed
        """
        params = {
            "key": self.api_key
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
            }
        }
        
        # Exponential backoff parameters
        max_retries = 5
        retry_count = 0
        base_delay = 2  # Base delay in seconds
        max_delay = 60  # Maximum delay in seconds
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    # Calculate exponential backoff delay
                    delay = min(max_delay, base_delay * (2 ** (retry_count - 1)))
                    if self.debug:
                        print(f"Debug: Retrying after {delay} seconds (attempt {retry_count}/{max_retries})...")
                    time.sleep(delay)
                
                response = requests.post(
                    self.api_url,
                    params=params,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if self.debug:
                    print(f"Debug: Gemini API response status: {response.status_code}")
                
                # If we get a 429, retry with exponential backoff
                if response.status_code == 429:
                    retry_count += 1
                    print(f"Rate limit exceeded (429). Retrying ({retry_count}/{max_retries})...")
                    continue
                
                # For other errors or success, proceed as usual
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                # If it's a rate limit error, retry with backoff
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"Rate limit exceeded (429). Retrying ({retry_count}/{max_retries})...")
                        continue
                
                # For other errors or if we've exceeded max retries
                print(f"Error calling Gemini API: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response status code: {e.response.status_code}")
                    print(f"Response content: {e.response.text[:1000]}")
                return None
        
        # If we've exhausted all retries
        print(f"Failed after {max_retries} retries. Giving up on this request.")
        return None
    
    def _parse_gemini_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the response from the Gemini API.
        
        Args:
            response: The raw API response
            
        Returns:
            Dictionary with the parsed analysis results
        """
        try:
            # Extract the text from the response
            text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if not text:
                return {
                    "success": False,
                    "message": "Empty response from Gemini API",
                    "discrepancies": []
                }
            
            # Try to extract JSON from the response
            # Look for JSON content between triple backticks if present
            if "```json" in text and "```" in text.split("```json", 1)[1]:
                json_text = text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in text and "```" in text.split("```", 1)[1]:
                json_text = text.split("```", 1)[1].split("```", 1)[0].strip()
            else:
                json_text = text
            
            # Parse the JSON
            try:
                analysis = json.loads(json_text)
                return {
                    "success": True,
                    "analysis": analysis
                }
            except json.JSONDecodeError:
                if self.debug:
                    print(f"Debug: Could not parse JSON from response: {json_text[:500]}")
                
                # If we couldn't parse JSON, return the raw text
                return {
                    "success": True,
                    "analysis": {
                        "summary": "Analysis results could not be parsed as JSON",
                        "raw_text": text,
                        "discrepancies": []
                    }
                }
                
        except Exception as e:
            print(f"Error parsing Gemini response: {str(e)}")
            return {
                "success": False,
                "message": f"Error parsing response: {str(e)}",
                "discrepancies": []
            }
    
    def analyze_files(self, content_dir: str, style_guide_path: str, 
                      output_file: str, batch_size: int = 1, 
                      delay: float = 1.0, ai_guide_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze multiple files against a style guide.
        
        Args:
            content_dir: Directory containing files to analyze
            style_guide_path: Path to the style guide file
            output_file: Path to save analysis results
            batch_size: Number of files to analyze in a batch (1 means process one by one)
            delay: Delay between API calls in seconds
            ai_guide_path: Optional path to an AI-specific guidance file
            
        Returns:
            List of analysis results for each file
        """
        # Read the style guide
        try:
            with open(style_guide_path, 'r', encoding='utf-8') as f:
                style_guide = f.read()
                
            if self.debug:
                print(f"Debug: Read style guide from {style_guide_path} ({len(style_guide)} chars)")
        except Exception as e:
            print(f"Error reading style guide file: {str(e)}")
            return []
        
        # Read the AI guide if provided
        ai_guide = None
        if ai_guide_path:
            try:
                with open(ai_guide_path, 'r', encoding='utf-8') as f:
                    ai_guide = f.read()
                    
                if self.debug:
                    print(f"Debug: Read AI guide from {ai_guide_path} ({len(ai_guide)} chars)")
            except Exception as e:
                print(f"Error reading AI guide file: {str(e)}")
                # Continue with just the style guide if AI guide can't be read
        
        # Find all .md and .html files in the content directory
        content_files = []
        for ext in ['.md', '.html']:
            content_files.extend(list(Path(content_dir).glob(f"**/*{ext}")))
        
        if self.debug:
            print(f"Debug: Found {len(content_files)} files to analyze")
            
        if not content_files:
            print(f"No content files found in {content_dir}")
            return []
        
        # Process files
        results = []
        
        for i, file_path in enumerate(content_files):
            rel_path = file_path.relative_to(content_dir)
            print(f"[{i+1}/{len(content_files)}] Analyzing {rel_path}...", end="", flush=True)
            
            try:
                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analyze the content
                analysis = self.analyze_content(content, style_guide, ai_guide)
                
                # Add file information
                file_result = {
                    "file_path": str(rel_path),
                    "file_size": len(content),
                    "analysis": analysis
                }
                
                results.append(file_result)
                
                if analysis["success"]:
                    print(" ✓")
                else:
                    print(" ✗")
                
                # Save intermediate results
                self._save_results(results, output_file)
                
                # Add delay between API calls
                if i < len(content_files) - 1:
                    # Add jitter to delay to help prevent rate limiting
                    jitter = random.uniform(0.5, 1.5)  # Random factor between 0.5 and 1.5
                    adjusted_delay = delay * jitter
                    if self.debug:
                        print(f"Debug: Waiting {adjusted_delay:.2f}s before next file (base: {delay}s, jitter: {jitter:.2f}x)")
                    time.sleep(adjusted_delay)
                    
            except Exception as e:
                print(f" Error: {str(e)}")
                results.append({
                    "file_path": str(rel_path),
                    "error": str(e)
                })
        
        # Final save
        self._save_results(results, output_file)
        
        return results
    
    def _save_results(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Save analysis results to a file.
        
        Args:
            results: List of analysis results
            output_file: Path to save the results
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            if self.debug:
                print(f"Debug: Saved results to {output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")
    
    def create_readable_report(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Create a readable HTML report from analysis results.
        
        Args:
            results: List of analysis results
            output_file: Path to save the report
        """
        # Count files with issues
        files_with_issues = sum(1 for r in results if r.get("analysis", {}).get("success", False) and 
                               len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) > 0)
        
        total_files = len(results)
        total_issues = sum(len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) 
                          for r in results if r.get("analysis", {}).get("success", False))
        
        # Calculate average compliance score
        compliance_scores = [r.get("analysis", {}).get("analysis", {}).get("compliance_score", 0) 
                           for r in results if r.get("analysis", {}).get("success", False)]
        avg_compliance = sum(float(score) for score in compliance_scores if isinstance(score, (int, float, str)) and str(score).replace('.', '', 1).isdigit()) / len(compliance_scores) if compliance_scores else 0
        
        # Create HTML report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki Content Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ margin-top: 1.5em; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .file {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        .file-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .issue {{ background-color: #fff8e1; padding: 10px; margin: 10px 0; border-left: 4px solid #ffc107; }}
        .issue.high {{ border-left: 4px solid #f44336; background-color: #ffebee; }}
        .issue.medium {{ border-left: 4px solid #ff9800; background-color: #fff3e0; }}
        .issue.low {{ border-left: 4px solid #4caf50; background-color: #e8f5e9; }}
        .issue-header {{ display: flex; justify-content: space-between; }}
        .severity {{ font-size: 0.8em; padding: 2px 6px; border-radius: 3px; color: white; }}
        .severity.high {{ background-color: #f44336; }}
        .severity.medium {{ background-color: #ff9800; }}
        .severity.low {{ background-color: #4caf50; }}
        .suggestion {{ background-color: #e3f2fd; padding: 10px; margin-top: 5px; }}
        .progress-bar {{ height: 15px; background-color: #e0e0e0; border-radius: 10px; margin: 10px 0; }}
        .progress {{ height: 100%; border-radius: 10px; background-color: #4caf50; }}
    </style>
</head>
<body>
    <h1>Wiki Content Analysis Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Files Analyzed:</strong> {total_files}</p>
        <p><strong>Files with Issues:</strong> {files_with_issues} ({files_with_issues/total_files*100:.1f}% of total)</p>
        <p><strong>Total Issues Found:</strong> {total_issues}</p>
        <p><strong>Average Compliance Score:</strong> {avg_compliance:.1f}/100</p>
        <div class="progress-bar">
            <div class="progress" style="width: {avg_compliance}%;"></div>
        </div>
    </div>
    
    <h2>Files with Issues</h2>
"""
        
        # Sort results by number of issues (most issues first)
        sorted_results = sorted(
            results, 
            key=lambda r: len(r.get("analysis", {}).get("analysis", {}).get("discrepancies", [])) if r.get("analysis", {}).get("success", False) else 0,
            reverse=True
        )
        
        # Add file sections
        for result in sorted_results:
            file_path = result.get("file_path", "Unknown file")
            
            if not result.get("analysis", {}).get("success", False):
                html += f"""
    <div class="file">
        <div class="file-header">
            <h3>{file_path}</h3>
            <span>Error analyzing file</span>
        </div>
        <p>{result.get("error", "Unknown error")}</p>
    </div>
"""
                continue
                
            analysis = result.get("analysis", {}).get("analysis", {})
            discrepancies = analysis.get("discrepancies", [])
            compliance_score = analysis.get("compliance_score", "N/A")
            
            if isinstance(compliance_score, str) and not compliance_score.replace('.', '', 1).isdigit():
                compliance_score = "N/A"
                
            if not discrepancies:
                continue  # Skip files with no issues
                
            html += f"""
    <div class="file">
        <div class="file-header">
            <h3>{file_path}</h3>
            <span>Compliance Score: {compliance_score}/100</span>
        </div>
        <div class="progress-bar">
            <div class="progress" style="width: {compliance_score if isinstance(compliance_score, (int, float)) or (isinstance(compliance_score, str) and compliance_score.replace('.', '', 1).isdigit()) else 0}%;"></div>
        </div>
        <p><strong>Summary:</strong> {analysis.get("summary", "No summary available")}</p>
        
        <h4>Discrepancies ({len(discrepancies)})</h4>
"""
            
            # Add issues
            for issue in discrepancies:
                severity = issue.get("severity", "medium").lower()
                html += f"""
        <div class="issue {severity}">
            <div class="issue-header">
                <strong>{issue.get("issue", "Issue")}</strong>
                <span class="severity {severity}">{severity.upper()}</span>
            </div>
            <p><strong>Location:</strong> {issue.get("location", "Unknown")}</p>
            <div class="suggestion">
                <strong>Suggestion:</strong> {issue.get("suggestion", "No suggestion available")}
            </div>
        </div>
"""
            
            html += """
    </div>
"""
        
        # Close HTML
        html += """
    <script>
        // Add any JavaScript here if needed
    </script>
</body>
</html>
"""
        
        # Save the HTML report
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
                
            print(f"✓ Readable report saved to {output_file}")
        except Exception as e:
            print(f"Error saving HTML report: {str(e)}")
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List available Gemini models.
        
        Returns:
            List of available models
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        
        try:
            response = requests.get(url)
            
            if self.debug:
                print(f"Debug: Models API response status: {response.status_code}")
            
            response.raise_for_status()
            models = response.json().get('models', [])
            
            # Filter for Gemini models only
            gemini_models = [m for m in models if 'gemini' in m.get('name', '').lower()]
            
            if self.debug:
                print(f"Debug: Found {len(gemini_models)} Gemini models")
                
            return gemini_models
            
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving Gemini models: {str(e)}")
            return [] 
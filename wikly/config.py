"""
Configuration utilities for Wiki.js Exporter.
"""

import os
import yaml
from typing import Dict, Any, Optional, Tuple

# Default config file path
DEFAULT_CONFIG_PATH = "wikly_config.yaml"

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with configuration values
    """
    import click
    
    default_config = {
        "wikly": {
            "host": None,
            "api_key": None,
            "use_env_vars": True,
        },
        "export": {
            "default_format": "markdown",
            "default_output": "wiki_export",
            "delay": 0.1,
            "metadata_file": ".wikly_export_metadata.json"
        },
        "gemini": {
            "api_key": None,
            "delay": 1.0,
            "default_model": "gemini-2.0-flash",
            "style_guide_file": "wiki_style_guide.md",
            "ai_guide_file": "ai_instructions.md",
            "metadata_file": ".wikly_analysis_metadata.json"
        },
        "sitemap": {
            "max_chars": 10000,
            "detail_level": 2,
            "show_by_default": False
        }
    }
    
    if not config_path:
        config_path = DEFAULT_CONFIG_PATH
    
    # Try to load the configuration file
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                click.echo(f"✓ Loaded configuration from {config_path}")
                
                # Convert string "None" values to Python None
                def convert_none_strings(d):
                    for k, v in d.items():
                        if isinstance(v, dict):
                            convert_none_strings(v)
                        elif v == "None" or v == "null":
                            d[k] = None
                
                # Process the loaded config
                if config:
                    convert_none_strings(config)
                
                # Merge with default config
                for section in default_config:
                    if section not in config:
                        config[section] = default_config[section]
                    else:
                        for key in default_config[section]:
                            if key not in config[section]:
                                config[section][key] = default_config[section][key]
                
                # Print debug info about API keys
                if config.get("wikly", {}).get("api_key") is None:
                    click.echo("Note: Wiki.js API key not found in config, will try environment variables")
                if config.get("gemini", {}).get("api_key") is None:
                    click.echo("Note: Gemini API key not found in config, will try environment variables")
                
                return config
    except Exception as e:
        click.echo(f"Warning: Error loading configuration file: {str(e)}")
    
    # Return default configuration if loading fails
    return default_config

def create_sample_style_guide():
    """Create a sample style guide for wiki content."""
    return """# Wiki Content Style Guide

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

def create_sample_ai_guide():
    """Create sample AI-specific instructions for content analysis."""
    return """# AI-Specific Analysis Instructions

These instructions are intended for the AI analyzer only and supplement the main style guide.

## Analysis Context
When analyzing wiki content, consider the following additional factors:

1. **Technical Accuracy**: While you cannot verify factual accuracy of domain-specific content, flag statements that appear logically inconsistent or potentially misleading.

2. **Audience Appropriateness**: Our wiki content is intended for technical users with varying levels of expertise. Content should avoid assuming too much prior knowledge but should also not over-explain basic concepts.

3. **Consistency Across Pages**: Flag terminology or formatting that differs significantly from typical patterns in technical documentation.

## Analysis Priorities

Please prioritize issues in this order:
1. Structural problems that affect readability (missing sections, poor organization)
2. Technical clarity issues (ambiguous instructions, unclear explanations)
3. Style and formatting inconsistencies
4. Language and grammar issues

## Response Format

When identifying issues:
- Provide specific, actionable suggestions for improvement
- Consider the context of technical documentation when making recommendations
- Provide severity ratings (high, medium, low) based on how much the issue impacts reader understanding

## Content Types

Our wiki contains several types of content, each with specific requirements:

1. **Tutorials**: Should have clear, sequential steps with expected outcomes stated.
2. **Reference Pages**: Should be comprehensive and well-organized with consistent formatting.
3. **Concept Explanations**: Should build understanding progressively and provide examples.
4. **Troubleshooting Guides**: Should clearly describe problems and solutions with debugging steps.

Please consider the content type when analyzing for style compliance.
""" 
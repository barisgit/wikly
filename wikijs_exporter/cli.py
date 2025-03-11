"""
Command-line interface for Wiki.js Exporter.
"""

import click

from .commands.init import init_config
from .commands.test import test_connection
from .commands.list_pages import list_pages
from .commands.export import export_pages
from .commands.analyze import analyze_content
from .commands.report import generate_report
from .commands.models import list_gemini_models

@click.group()
@click.version_option()
def cli():
    """Wiki.js Exporter - Export content from a Wiki.js instance."""
    pass

# Register all commands
cli.add_command(init_config)
cli.add_command(test_connection)
cli.add_command(list_pages)
cli.add_command(export_pages)
cli.add_command(analyze_content)
cli.add_command(generate_report)
cli.add_command(list_gemini_models)

if __name__ == '__main__':
    cli() 
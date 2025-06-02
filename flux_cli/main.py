"""Main CLI entry point for Flux API CLI."""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .commands.generate import generate
from .commands.recover import recover

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flux_cli.log')
    ]
)

# Only add console handler if debug mode is enabled
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)  # Only show warnings and errors on console

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@click.group()
@click.version_option(version="0.1.0", prog_name="Flux CLI")
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug logging"
)
def cli(debug: bool):
    """Flux API CLI - Generate images using Black Forest Labs' Flux models.
    
    A command-line tool for interacting with the Flux API to generate
    images from text prompts using advanced AI models.
    
    Examples:
        flux generate --prompt "A beautiful sunset"
        flux history --last 10
        flux config set default-model flux-kontext-max
    """
    if debug:
        # In debug mode, show all logs in console
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(console_handler)
        console_handler.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        # In normal mode, only show warnings/errors
        logging.getLogger().addHandler(console_handler)


# Add commands
cli.add_command(generate)
cli.add_command(recover)


# Placeholder commands (to be implemented)
@cli.command()
@click.option("--last", "-n", type=int, help="Show last N generations")
@click.option("--status", "-s", help="Filter by status")
@click.option("--model", "-m", help="Filter by model")
def history(last: int, status: str, model: str):
    """View generation history."""
    click.echo("History command not yet implemented")


@cli.command()
@click.argument("generation_id")
@click.option("--prompt", "-p", help="New prompt (optional)")
@click.option("--seed", "-s", type=int, help="New seed (optional)")
def regenerate(generation_id: str, prompt: str, seed: int):
    """Re-run a previous generation."""
    click.echo("Regenerate command not yet implemented")


@cli.group()
def config():
    """Manage configuration settings."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set a configuration value."""
    click.echo(f"Config set command not yet implemented: {key}={value}")


@config.command()
@click.argument("key")
def get(key: str):
    """Get a configuration value."""
    click.echo(f"Config get command not yet implemented: {key}")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Show what would be generated")
def batch(input_file: str, dry_run: bool):
    """Process multiple prompts from a JSON file."""
    click.echo("Batch command not yet implemented")


def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
Mermaid-GIF CLI Entry Point

This module provides the command-line interface for converting Mermaid diagrams
or natural language descriptions into animated GIF files.

Usage:
    python -m src.main "Create a flowchart showing login process"
    python -m src.main --input-file diagram.mmd
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.config import get_config
from .core.graph import compile_graph
from .core.state import create_initial_state
from .utils.logger import configure_logging

# Initialize CLI app
app = typer.Typer(
    name="mermaid-gif",
    help="Convert Mermaid diagrams to animated GIFs using AI and browser automation",
    add_completion=False,
)

# Rich console for pretty output
console = Console()


def main(
    prompt: Optional[str] = typer.Argument(
        None,
        help="Natural language description or Mermaid diagram code",
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input-file",
        "-i",
        help="Path to file containing Mermaid diagram code",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for the generated GIF (default: auto-generated)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """
    Convert Mermaid diagrams to animated GIFs.
    
    Provide either a text prompt or a Mermaid diagram file.
    """
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    configure_logging()
    
    # Validate input
    if not prompt and not input_file:
        console.print(
            "[red]Error:[/red] You must provide either a prompt or an input file.",
            style="bold",
        )
        console.print("\nUsage examples:")
        console.print("  python -m src.main \"Create a flowchart of user login\"")
        console.print("  python -m src.main --input-file diagram.mmd")
        raise typer.Exit(1)
    
    if prompt and input_file:
        console.print(
            "[yellow]Warning:[/yellow] Both prompt and input file provided. Using input file.",
            style="bold",
        )
    
    try:
        # Determine input type and content
        if input_file:
            raw_input = input_file.read_text(encoding="utf-8")
            input_type = "mermaid"
            console.print(f"[cyan]Reading Mermaid diagram from:[/cyan] {input_file}")
        else:
            raw_input = prompt
            input_type = "text"
            console.print(f"[cyan]Processing prompt:[/cyan] {prompt}")
        
        # Initialize state
        initial_state = create_initial_state(
            raw_input=raw_input,
            input_type=input_type,
        )
        
        # Compile graph
        console.print("\n[cyan]Initializing LangGraph workflow...[/cyan]")
        graph = compile_graph()
        
        # Execute workflow with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Generating animated GIF...",
                total=None,
            )
            
            # Run the graph
            final_state = graph.invoke(initial_state)
            
            progress.update(task, completed=True)
        
        # Check for errors
        errors = final_state.get("errors", [])
        if errors:
            console.print("\n[red]Errors occurred during generation:[/red]", style="bold")
            for error in errors:
                console.print(f"  • {error}", style="red")
            raise typer.Exit(1)
        
        # Check for successful output
        gif_path = final_state.get("gif_path")
        if not gif_path:
            console.print(
                "\n[red]Error:[/red] GIF generation failed - no output path in state",
                style="bold",
            )
            raise typer.Exit(1)
        
        # Verify output file exists
        gif_file = Path(gif_path)
        if not gif_file.exists():
            console.print(
                f"\n[red]Error:[/red] GIF file not found at {gif_path}",
                style="bold",
            )
            raise typer.Exit(1)
        
        # Move to output location if specified
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy(gif_file, output)
            final_path = output
        else:
            final_path = gif_file
        
        # Success output
        file_size = final_path.stat().st_size / 1024  # KB
        
        console.print("\n" + "=" * 60)
        console.print(
            Panel.fit(
                f"[green]✓ Success![/green]\n\n"
                f"[cyan]GIF saved to:[/cyan] {final_path}\n"
                f"[cyan]File size:[/cyan] {file_size:.1f} KB\n"
                f"[cyan]Mermaid code:[/cyan] {len(final_state.get('mermaid_code', ''))} characters",
                title="[bold green]Mermaid-GIF Generation Complete[/bold green]",
                border_style="green",
            )
        )
        console.print("=" * 60 + "\n")
        
        if verbose:
            console.print("\n[cyan]Final State Summary:[/cyan]")
            console.print(f"  • Diagram rendered: {final_state.get('diagram_rendered', False)}")
            console.print(f"  • Animation applied: {final_state.get('animation_applied', False)}")
            console.print(f"  • Video path: {final_state.get('video_path', 'N/A')}")
            console.print(f"  • Retry count: {final_state.get('retry_count', 0)}")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
        raise typer.Exit(130)
    
    except Exception as e:
        console.print(f"\n[red]Fatal error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback
            console.print("\n[red]Traceback:[/red]")
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def run(
    prompt: Optional[str] = typer.Argument(None),
    input_file: Optional[Path] = typer.Option(None, "--input-file", "-i"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the Mermaid-GIF generator."""
    main(prompt, input_file, output, verbose)


if __name__ == "__main__":
    # Allow direct execution: python -m src.main
    app()

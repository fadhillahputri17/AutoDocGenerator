from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from autodocgenerator.application.factory import ApplicationSettings, build_workflow

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def run(
    input_directory: Annotated[
        Path,
        typer.Option("--input", "-i"),
    ] = Path("input"),
    output_directory: Annotated[
        Path,
        typer.Option("--output", "-o"),
    ] = Path("output"),
    company_name: Annotated[
        str,
        typer.Option("--company"),
    ] = "PT. XXXXXXX XXXXXX XXXXXXX",
    bank_name: Annotated[
        str,
        typer.Option("--bank"),
    ] = "BCA",
    tesseract_path: Annotated[
        Path | None,
        typer.Option("--tesseract"),
    ] = None,
) -> None:
    """Generate a Word document from input screenshots."""
    workflow = build_workflow(
        ApplicationSettings(
            company_name=company_name,
            bank_name=bank_name,
            tesseract_executable_path=tesseract_path,
        )
    )

    result = workflow.run(
        input_directory=input_directory,
        output_directory=output_directory,
        progress=console.print,
    )

    console.print(
        f"[bold green]Dokumen:[/bold green] {result.document_path}"
    )


@app.command()
def gui() -> None:
    """Open the desktop interface."""
    from autodocgenerator.presentation.desktop_app import (
        launch_desktop_app,
    )

    launch_desktop_app()


if __name__ == "__main__":
    app()

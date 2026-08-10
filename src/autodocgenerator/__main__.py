"""Package entry point for AutoDocGenerator."""

from autodocgenerator.presentation.desktop_app import (
    launch_desktop_app,
)


def main() -> None:
    """Launch the AutoDocGenerator desktop application."""
    launch_desktop_app()


if __name__ == "__main__":
    main()

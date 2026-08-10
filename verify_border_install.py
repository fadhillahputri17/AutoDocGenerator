from __future__ import annotations

from pathlib import Path

import autodocgenerator.services.image_processor as module
from autodocgenerator.services.image_processor import (
    ImageProcessingSettings,
    ImageProcessor,
)


def main() -> None:
    module_path = Path(module.__file__).resolve()
    settings = ImageProcessingSettings()

    print(f"MODULE FILE: {module_path}")
    print(
        "HAS _detect_semantic_transaction_box:",
        hasattr(ImageProcessor, "_detect_semantic_transaction_box"),
    )
    print(
        "HAS _add_border:",
        hasattr(ImageProcessor, "_add_border"),
    )
    print(
        "DEFAULT BORDER:",
        settings.border_width_pt,
        "pt",
    )

    expected = (
        Path.cwd()
        / "src"
        / "autodocgenerator"
        / "services"
        / "image_processor.py"
    ).resolve()

    print(f"EXPECTED FILE: {expected}")
    print("CORRECT FILE:", module_path == expected)


if __name__ == "__main__":
    main()

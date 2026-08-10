from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from autodocgenerator.application.workflow import AutoDocWorkflow
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)
from autodocgenerator.services.file_loader import FileLoader
from autodocgenerator.services.image_processor import ImageProcessor
from autodocgenerator.services.image_sorter import ImageSorter
from autodocgenerator.services.ocr import OCRProcessor


def create_image(
    path: Path,
    size: tuple[int, int],
) -> None:
    """Create a valid image for integration testing."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    Image.new(
        "RGB",
        size,
        "white",
    ).save(path)


def test_end_to_end_with_mocked_ocr_and_crop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Run the complete workflow with border-enabled image processing."""
    transfer = (
        tmp_path
        / "input"
        / "TRANSFER"
        / "transfer.jpg"
    )
    receipt = (
        tmp_path
        / "input"
        / "NOTA REAL"
        / "nota.jpg"
    )

    create_image(
        transfer,
        (800, 1200),
    )
    create_image(
        receipt,
        (600, 900),
    )

    ocr_engine = Mock()
    ocr_engine.read.return_value = (
        """
        Pelaksana Transaksi
        VOLVO960 Dibuat 28/07/2026 10:30:45
        VOLVO960 Diotorisasi 28/07/2026 10:45:00
        """,
        90.0,
    )

    def fake_adaptive_crop(
        self: ImageProcessor,
        image: Image.Image,
    ) -> Image.Image:
        del self
        return image.crop(
            (
                0,
                150,
                image.width,
                950,
            )
        )

    monkeypatch.setattr(
        ImageProcessor,
        "_adaptive_transfer_crop",
        fake_adaptive_crop,
    )

    workflow = AutoDocWorkflow(
        file_loader=FileLoader(),
        ocr_processor=OCRProcessor(
            engine=ocr_engine,
        ),
        image_sorter=ImageSorter(),
        image_processor=ImageProcessor(),
        document_generator=DocumentGenerator(
            settings=DocumentGenerationSettings(
                company_name="PT. TEST INDONESIA",
                bank_name="BCA",
            )
        ),
    )

    result = workflow.run(
        input_directory=tmp_path / "input",
        output_directory=tmp_path / "output",
    )

    assert result.document_path.exists()
    assert result.image_count == 2
    assert result.review_count == 0

    processed_directory = (
        result.run_directory
        / "processed_images"
    )
    processed_images = sorted(
        path
        for path in processed_directory.iterdir()
        if path.is_file()
        and path.suffix.casefold() in {
            ".jpg",
            ".jpeg",
            ".png",
        }
    )

    assert len(processed_images) == 2

    transfer_output = next(
        path
        for path in processed_images
        if "transfer" in path.stem.casefold()
    )
    receipt_output = next(
        path
        for path in processed_images
        if "nota" in path.stem.casefold()
    )

    assert transfer_output.suffix.casefold() == ".jpg"
    assert receipt_output.suffix.casefold() == ".png"

    with Image.open(transfer_output) as transfer_image:
        # Fake crop: 800 x 800.
        # Border 1.5 pt at 96 DPI: 2 px per side.
        assert transfer_image.size == (804, 804)

    with Image.open(receipt_output) as receipt_image:
        # Original receipt: 600 x 900.
        # Border 1.5 pt at 96 DPI: 2 px per side.
        assert receipt_image.size == (604, 904)

    ocr_engine.read.assert_called_once_with(
        transfer.resolve()
    )

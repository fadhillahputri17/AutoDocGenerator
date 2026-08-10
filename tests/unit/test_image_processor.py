from pathlib import Path

import pytest
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.image_processor import (
    ImageProcessingSettings,
    ImageProcessor,
)


def create_image(
    path: Path,
    size: tuple[int, int],
) -> None:
    """Create a valid white RGB image for testing."""
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    Image.new(
        "RGB",
        size,
        "white",
    ).save(path)


def test_transfer_is_cropped_with_1_5_pt_border(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transfer must be cropped, then receive a 1.5 pt border."""
    source_path = tmp_path / "transfer.jpg"
    create_image(
        source_path,
        (800, 1200),
    )

    def fake_box(
        self: ImageProcessor,
        image: Image.Image,
    ) -> tuple[int, int, int, int]:
        del self
        return (
            0,
            200,
            image.width,
            900,
        )

    monkeypatch.setattr(
        ImageProcessor,
        "_detect_semantic_transaction_box",
        fake_box,
    )

    source_image = SourceImage(
        path=source_path,
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    processor = ImageProcessor(
        settings=ImageProcessingSettings(
            border_width_pt=1.5,
            output_dpi=96,
            transfer_square_output=False,
            title_padding_ratio=0.0,
            bottom_padding_ratio=0.0,
            transfer_content_padding_px=0,
        )
    )

    processor.process_all(
        [source_image],
        tmp_path / "output",
    )

    assert source_image.processed_path is not None
    assert source_image.processed_path.exists()

    with Image.open(source_image.processed_path) as result:
        result_rgb = result.convert("RGB")

        # Crop result: 800 x 700.
        # Border: 2 px on each side, so final size is 804 x 704.
        assert result_rgb.size == (804, 704)

        border_pixel = result_rgb.getpixel((0, 0))
        inner_pixel = result_rgb.getpixel((2, 2))

        # JPEG compression can slightly change exact RGB values.
        assert max(border_pixel) < 40
        assert min(inner_pixel) > 220


def test_real_receipt_keeps_content_and_gets_1_5_pt_border(
    tmp_path: Path,
) -> None:
    """REAL RECEIPT must stay uncropped and receive a 1.5 pt border."""
    source_path = tmp_path / "nota.jpg"
    create_image(
        source_path,
        (600, 900),
    )

    source_image = SourceImage(
        path=source_path,
        image_type=DocumentImageType.REAL_RECEIPT,
    )

    ImageProcessor(
        settings=ImageProcessingSettings(
            border_width_pt=1.5,
            output_dpi=96,
        )
    ).process_all(
        [source_image],
        tmp_path / "output",
    )

    assert source_image.processed_path is not None
    assert source_image.processed_path.exists()

    with Image.open(source_image.processed_path) as result:
        result_rgb = result.convert("RGB")

        # Original: 600 x 900.
        # Border: 2 px on each side, so final size is 604 x 904.
        assert result_rgb.size == (604, 904)
        assert result_rgb.getpixel((0, 0)) == (0, 0, 0)
        assert result_rgb.getpixel((2, 2)) == (255, 255, 255)


def test_output_names_use_sequence_number(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Processed files must use deterministic sequence numbers."""
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"

    create_image(
        first_path,
        (500, 700),
    )
    create_image(
        second_path,
        (500, 700),
    )

    def full_image_box(
        self: ImageProcessor,
        image: Image.Image,
    ) -> tuple[int, int, int, int]:
        del self
        return (
            0,
            0,
            image.width,
            image.height,
        )

    monkeypatch.setattr(
        ImageProcessor,
        "_detect_semantic_transaction_box",
        full_image_box,
    )

    images = [
        SourceImage(
            path=first_path,
            image_type=DocumentImageType.TRANSFER_PROOF,
        ),
        SourceImage(
            path=second_path,
            image_type=DocumentImageType.TRANSFER_PROOF,
        ),
    ]

    ImageProcessor(
        settings=ImageProcessingSettings(
            border_width_pt=1.5,
            output_dpi=96,
            transfer_square_output=False,
        )
    ).process_all(
        images,
        tmp_path / "output",
    )

    assert images[0].processed_path is not None
    assert images[1].processed_path is not None

    assert images[0].processed_path.exists()
    assert images[1].processed_path.exists()

    assert images[0].processed_path.name.startswith("001_")
    assert images[1].processed_path.name.startswith("002_")
    assert (
        images[0].processed_path.name
        != images[1].processed_path.name
    )

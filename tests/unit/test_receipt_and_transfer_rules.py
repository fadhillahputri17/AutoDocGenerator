from pathlib import Path

import pymupdf
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.file_loader import FileLoader
from autodocgenerator.services.image_processor import (
    ImageProcessor,
    _OCRLine,
)


def test_loader_accepts_nested_pdf_in_normalized_nota_real_folder(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path
        / "arsip"
        / "Nota_Real"
        / "dokumen"
        / "Reimburse Pakan.pdf"
    )
    pdf_path.parent.mkdir(parents=True)

    document = pymupdf.open()
    document.new_page(
        width=300,
        height=500,
    )
    document.save(pdf_path)
    document.close()

    loaded = FileLoader().load(tmp_path)

    assert [item.path for item in loaded] == [
        pdf_path.resolve()
    ]
    assert loaded[0].is_pdf_receipt is True


def test_real_receipt_keeps_content_and_gets_border(
    tmp_path: Path,
) -> None:
    source_path = (
        tmp_path
        / "NOTA REAL"
        / "nota.jpg"
    )
    source_path.parent.mkdir(parents=True)

    Image.new(
        "RGB",
        (320, 480),
        "white",
    ).save(
        source_path,
        quality=87,
    )

    source = SourceImage(
        path=source_path,
        image_type=DocumentImageType.REAL_RECEIPT,
    )

    ImageProcessor().process_all(
        [source],
        tmp_path / "output",
    )

    assert source.processed_path is not None
    assert source.processed_path.exists()
    assert source.processed_path.suffix.casefold() == ".png"

    with Image.open(source.processed_path) as result:
        result_rgb = result.convert("RGB")

        # Original: 320 x 480.
        # Border 1.5 pt at 96 DPI: 2 px per side.
        assert result_rgb.size == (324, 484)
        assert result_rgb.getpixel((0, 0)) == (0, 0, 0)
        assert result_rgb.getpixel((2, 2)) == (
            255,
            255,
            255,
        )


def test_transfer_crop_uses_transfer_dana_and_diotorisasi_bounds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "transfer.jpg"
    Image.new(
        "RGB",
        (800, 1200),
        "white",
    ).save(source_path)

    lines = [
        _OCRLine(
            "Toolbar browser",
            0,
            20,
            300,
            50,
        ),
        _OCRLine(
            "Transfer Dana ke rekening BCA",
            60,
            180,
            650,
            220,
        ),
        _OCRLine(
            "Informasi Transfer",
            60,
            260,
            650,
            300,
        ),
        _OCRLine(
            "VOLVO960 Dibuat 14/07/2026 10:00:00",
            60,
            700,
            700,
            740,
        ),
        _OCRLine(
            "VOLVO960 Diotorisasi 14/07/2026 10:05:00",
            60,
            820,
            720,
            860,
        ),
        _OCRLine(
            "Tombol Cetak",
            60,
            1050,
            300,
            1090,
        ),
    ]

    monkeypatch.setattr(
        ImageProcessor,
        "_read_ocr_lines",
        lambda self, image: lines,
    )

    source = SourceImage(
        path=source_path,
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    ImageProcessor().process_all(
        [source],
        tmp_path / "output",
    )

    assert source.processed_path is not None

    with Image.open(source.processed_path) as result:
        result_rgb = result.convert("RGB")

        # Full horizontal width remains 800 px.
        # Border adds 2 px on the left and right.
        assert result_rgb.width == 804

        # Crop begins slightly above "Transfer Dana" and ends slightly
        # below "Diotorisasi", then receives a 2 px border per side.
        assert result_rgb.height == 703

        border_pixel = result_rgb.getpixel((0, 0))
        assert max(border_pixel) < 40

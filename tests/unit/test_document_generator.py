from datetime import date, datetime
from pathlib import Path

import pytest
from docx import Document
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.exceptions import DocumentGenerationError
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)


def processed_image(
    tmp_path: Path,
    name: str,
    image_type: DocumentImageType,
    *,
    size: tuple[int, int] = (600, 900),
    transaction_datetime: datetime | None = None,
) -> SourceImage:
    path = tmp_path / name
    Image.new("RGB", size, "white").save(path)

    return SourceImage(
        path=path,
        image_type=image_type,
        processed_path=path,
        transaction_datetime=transaction_datetime,
    )


def generator() -> DocumentGenerator:
    return DocumentGenerator(
        settings=DocumentGenerationSettings(
            company_name="PT. TEST INDONESIA",
            bank_name="BCA",
        )
    )


def test_generate_creates_docx_with_expected_title(tmp_path: Path) -> None:
    image = processed_image(
        tmp_path,
        "transfer.jpg",
        DocumentImageType.TRANSFER_PROOF,
        transaction_datetime=datetime(2026, 7, 28, 10, 0, 0),
    )

    output = generator().generate(
        [image],
        tmp_path / "output",
        document_date=date(2026, 7, 28),
    )

    assert output.exists()
    assert output.name == "BUKTI PENGELUARAN TGL 28 JULI 2026.docx"

    document = Document(output)
    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "BUKTI PENGELUARAN TGL 28 JULI 2026" in full_text
    assert "PT. TEST INDONESIA" in full_text
    assert "(BCA)" in full_text


def test_resolve_date_uses_earliest_transaction_datetime(tmp_path: Path) -> None:
    later = processed_image(
        tmp_path,
        "later.jpg",
        DocumentImageType.TRANSFER_PROOF,
        transaction_datetime=datetime(2026, 7, 29, 9, 0, 0),
    )
    earlier = processed_image(
        tmp_path,
        "earlier.jpg",
        DocumentImageType.TRANSFER_PROOF,
        transaction_datetime=datetime(2026, 7, 28, 12, 0, 0),
    )

    output = generator().generate([later, earlier], tmp_path / "output")

    assert output.name == "BUKTI PENGELUARAN TGL 28 JULI 2026.docx"


def test_receipt_dimensions_preserve_aspect_ratio(tmp_path: Path) -> None:
    receipt = processed_image(
        tmp_path,
        "nota.jpg",
        DocumentImageType.REAL_RECEIPT,
        size=(500, 1000),
    )

    width, height = generator()._fit_dimensions(
        receipt.processed_path,
        14.0,
        22.0,
    )

    assert width == pytest.approx(11.0)
    assert height == pytest.approx(22.0)


def test_generate_rejects_no_usable_images(tmp_path: Path) -> None:
    image = SourceImage(
        path=tmp_path / "missing.jpg",
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    with pytest.raises(DocumentGenerationError):
        generator().generate([image], tmp_path / "output")

from datetime import datetime
from pathlib import Path

from autodocgenerator.domain.enums import DatetimeSource, DocumentImageType
from autodocgenerator.domain.models import SourceImage


def test_source_image_converts_paths_and_exposes_properties() -> None:
    image = SourceImage(
        path="input/transfer.jpg",
        image_type=DocumentImageType.TRANSFER_PROOF,
        transaction_datetime=datetime(2026, 7, 28, 10, 30, 45),
        datetime_source=DatetimeSource.OCR_BCA_CREATED,
        processed_path="output/001_transfer.jpg",
    )

    assert image.path == Path("input/transfer.jpg")
    assert image.processed_path == Path("output/001_transfer.jpg")
    assert image.filename == "transfer.jpg"
    assert image.is_transfer_proof is True
    assert image.is_real_receipt is False


def test_real_receipt_property() -> None:
    image = SourceImage(
        path=Path("input/NOTA REAL/nota.jpg"),
        image_type=DocumentImageType.REAL_RECEIPT,
    )

    assert image.is_real_receipt is True
    assert image.is_transfer_proof is False

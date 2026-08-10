from pathlib import Path
from unittest.mock import Mock

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.exceptions import OCRProcessingError
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.ocr import OCRProcessor


def test_ocr_processor_populates_transfer_fields() -> None:
    engine = Mock()
    engine.read.return_value = (
        "Pelaksana Transaksi VOLVO960 Dibuat 28/07/2026 10:30:45",
        91.5,
    )

    transfer = SourceImage(
        path=Path("transfer.jpg"),
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    result = OCRProcessor(engine=engine).process_all([transfer])

    assert result == [transfer]
    assert transfer.ocr_text.startswith("Pelaksana Transaksi")
    assert transfer.ocr_confidence == 91.5
    assert transfer.requires_review is False
    engine.read.assert_called_once_with(Path("transfer.jpg"))


def test_ocr_processor_skips_real_receipt() -> None:
    engine = Mock()

    receipt = SourceImage(
        path=Path("nota.jpg"),
        image_type=DocumentImageType.REAL_RECEIPT,
    )

    OCRProcessor(engine=engine).process_all([receipt])

    engine.read.assert_not_called()
    assert receipt.ocr_text == ""


def test_ocr_error_marks_transfer_for_review() -> None:
    engine = Mock()
    engine.read.side_effect = OCRProcessingError("OCR gagal")

    transfer = SourceImage(
        path=Path("transfer.jpg"),
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    OCRProcessor(engine=engine).process_all([transfer])

    assert transfer.requires_review is True
    assert "OCR gagal" in transfer.warnings

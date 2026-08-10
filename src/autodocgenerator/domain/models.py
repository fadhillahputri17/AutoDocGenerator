from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from autodocgenerator.domain.enums import DatetimeSource, DocumentImageType


@dataclass(slots=True)
class SourceImage:
    """State carried by one source file through the workflow."""

    path: Path
    image_type: DocumentImageType = DocumentImageType.UNKNOWN
    transaction_datetime: datetime | None = None
    datetime_source: DatetimeSource | None = None
    reference_number: str | None = None
    ocr_text: str = ""
    ocr_confidence: float | None = None
    requires_review: bool = False
    warnings: list[str] = field(default_factory=list)
    processed_path: Path | None = None
    pdf_title: str | None = None
    pdf_page_number: int | None = None
    pdf_page_count: int | None = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)

        if self.processed_path is not None:
            self.processed_path = Path(self.processed_path)

        if self.pdf_title is not None:
            cleaned_title = self.pdf_title.strip()
            self.pdf_title = cleaned_title or None

        if self.pdf_page_number is not None and self.pdf_page_number < 1:
            raise ValueError("pdf_page_number must be greater than zero.")

        if self.pdf_page_count is not None and self.pdf_page_count < 1:
            raise ValueError("pdf_page_count must be greater than zero.")

        if (
            self.pdf_page_number is not None
            and self.pdf_page_count is not None
            and self.pdf_page_number > self.pdf_page_count
        ):
            raise ValueError(
                "pdf_page_number cannot be greater than pdf_page_count."
            )

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def is_real_receipt(self) -> bool:
        return self.image_type is DocumentImageType.REAL_RECEIPT

    @property
    def is_transfer_proof(self) -> bool:
        return self.image_type is DocumentImageType.TRANSFER_PROOF

    @property
    def is_pdf_receipt(self) -> bool:
        return (
            self.is_real_receipt
            and self.path.suffix.casefold() == ".pdf"
        )

    @property
    def is_first_pdf_page(self) -> bool:
        return self.is_pdf_receipt and self.pdf_page_number == 1

    @property
    def resolved_pdf_title(self) -> str:
        return self.pdf_title or self.path.stem

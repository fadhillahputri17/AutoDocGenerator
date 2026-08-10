from __future__ import annotations

from enum import StrEnum


class DocumentImageType(StrEnum):
    """Classification of an input image."""

    TRANSFER_PROOF = "transfer_proof"
    REAL_RECEIPT = "real_receipt"
    UNKNOWN = "unknown"


class DatetimeSource(StrEnum):
    """How the transaction datetime was obtained."""

    OCR_BCA_CREATED = "ocr_bca_created"
    OCR_BRI_TRANSACTION = "ocr_bri_transaction"
    OCR_GENERIC = "ocr_generic"
    OCR = "ocr"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"

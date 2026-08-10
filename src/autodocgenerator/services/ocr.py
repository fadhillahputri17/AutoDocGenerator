from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from pytesseract import Output

from autodocgenerator.domain.exceptions import OCRProcessingError
from autodocgenerator.domain.models import SourceImage


@dataclass(slots=True, frozen=True)
class OCRSettings:
    tesseract_executable_path: Path | None = None
    language: str = "eng"
    page_segmentation_mode: int = 6


class TesseractOCR:
    """Read OCR text and confidence from one image."""

    def __init__(self, *, settings: OCRSettings | None = None) -> None:
        self._settings = settings or OCRSettings()
        if self._settings.tesseract_executable_path is not None:
            pytesseract.pytesseract.tesseract_cmd = str(
                self._settings.tesseract_executable_path.expanduser().resolve()
            )

    def read(self, image_path: Path) -> tuple[str, float | None]:
        config = f"--oem 3 --psm {self._settings.page_segmentation_mode}"
        try:
            with Image.open(image_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                data = pytesseract.image_to_data(
                    image,
                    lang=self._settings.language,
                    config=config,
                    output_type=Output.DICT,
                )
        except (
            UnidentifiedImageError,
            OSError,
            pytesseract.TesseractError,
            pytesseract.TesseractNotFoundError,
        ) as error:
            raise OCRProcessingError(f"OCR gagal untuk: {image_path}") from error

        words: list[str] = []
        confidences: list[float] = []
        for raw_text, raw_confidence in zip(
            data.get("text", []),
            data.get("conf", []),
            strict=False,
        ):
            text = str(raw_text).strip()
            if text:
                words.append(text)
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                continue
            if confidence >= 0:
                confidences.append(confidence)

        text = " ".join(words)
        average = (
            sum(confidences) / len(confidences)
            if confidences
            else None
        )
        return text, average


class OCRProcessor:
    """Populate OCR fields for transfer images and skip NOTA REAL."""

    def __init__(self, *, engine: TesseractOCR | None = None) -> None:
        self._engine = engine or TesseractOCR()

    def process_all(self, images: list[SourceImage]) -> list[SourceImage]:
        for source_image in images:
            if source_image.is_real_receipt:
                continue
            try:
                text, confidence = self._engine.read(source_image.path)
                source_image.ocr_text = text
                source_image.ocr_confidence = confidence
            except OCRProcessingError as error:
                source_image.requires_review = True
                source_image.warnings.append(str(error))
        return images

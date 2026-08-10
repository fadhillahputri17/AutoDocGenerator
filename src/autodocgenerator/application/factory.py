from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autodocgenerator.application.workflow import AutoDocWorkflow
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)
from autodocgenerator.services.file_loader import FileLoader
from autodocgenerator.services.image_processor import (
    ImageProcessingSettings,
    ImageProcessor,
)
from autodocgenerator.services.image_sorter import ImageSorter
from autodocgenerator.services.ocr import OCRProcessor, OCRSettings, TesseractOCR


@dataclass(slots=True, frozen=True)
class ApplicationSettings:
    company_name: str
    bank_name: str = "BCA"
    tesseract_executable_path: Path | None = None


def build_workflow(settings: ApplicationSettings) -> AutoDocWorkflow:
    ocr_engine = TesseractOCR(
        settings=OCRSettings(
            tesseract_executable_path=settings.tesseract_executable_path,
        )
    )
    return AutoDocWorkflow(
        file_loader=FileLoader(),
        ocr_processor=OCRProcessor(engine=ocr_engine),
        image_sorter=ImageSorter(),
        image_processor=ImageProcessor(
            settings=ImageProcessingSettings(
                border_width_pt=0.0,
            )
        ),
        document_generator=DocumentGenerator(
            settings=DocumentGenerationSettings(
                company_name=settings.company_name,
                bank_name=settings.bank_name,
            )
        ),
    )

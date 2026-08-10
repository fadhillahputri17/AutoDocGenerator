from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from autodocgenerator.services.document_generator import DocumentGenerator
from autodocgenerator.services.file_loader import FileLoader
from autodocgenerator.services.image_processor import ImageProcessor
from autodocgenerator.services.image_sorter import ImageSorter
from autodocgenerator.services.ocr import OCRProcessor

ProgressCallback = Callable[[str], None]


@dataclass(slots=True, frozen=True)
class WorkflowResult:
    run_directory: Path
    document_path: Path
    image_count: int
    review_count: int


class AutoDocWorkflow:
    """Run the complete file-to-Word pipeline."""

    def __init__(
        self,
        *,
        file_loader: FileLoader,
        ocr_processor: OCRProcessor,
        image_sorter: ImageSorter,
        image_processor: ImageProcessor,
        document_generator: DocumentGenerator,
    ) -> None:
        self._file_loader = file_loader
        self._ocr_processor = ocr_processor
        self._image_sorter = image_sorter
        self._image_processor = image_processor
        self._document_generator = document_generator

    def run(
        self,
        *,
        input_directory: Path,
        output_directory: Path,
        progress: ProgressCallback | None = None,
        document_date: date | datetime | None = None,
    ) -> WorkflowResult:
        report = progress or (lambda _: None)
        run_directory = (
            output_directory.expanduser().resolve()
            / datetime.now().strftime("run_%Y%m%d_%H%M%S")
        )
        run_directory.mkdir(parents=True, exist_ok=True)

        report("Membaca file input...")
        source_files = self._file_loader.load(input_directory)
        report(f"Ditemukan {len(source_files)} file input unik.")

        report("Menjalankan OCR untuk bukti transfer...")
        self._ocr_processor.process_all(source_files)

        report("Mengurutkan transfer berdasarkan waktu Dibuat...")
        sorted_files = self._image_sorter.sort(source_files)

        report(
            "Memotong transfer dari Transfer Dana sampai Diotorisasi; "
            "nota real dipertahankan tanpa crop; PDF dirender per halaman..."
        )
        processed_images = self._image_processor.process_all(
            sorted_files,
            run_directory,
        )

        rendered_pdf_pages = sum(
            image.pdf_page_number is not None
            for image in processed_images
        )

        if rendered_pdf_pages:
            report(
                "PDF NOTA REAL berhasil dimasukkan: "
                f"{rendered_pdf_pages} halaman."
            )

        report("Membuat dokumen Word...")
        document_path = self._document_generator.generate(
            processed_images,
            run_directory,
            document_date=document_date,
        )

        review_images = [
            image
            for image in processed_images
            if image.requires_review
        ]
        review_directory = run_directory / "review"
        review_directory.mkdir(parents=True, exist_ok=True)
        review_report = review_directory / "review.txt"
        review_report.write_text(
            "\n".join(
                (
                    f"{image.path}: "
                    f"{'; '.join(image.warnings) or 'Perlu diperiksa'}"
                )
                for image in review_images
            ),
            encoding="utf-8",
        )

        report(f"Selesai: {document_path}")

        return WorkflowResult(
            run_directory=run_directory,
            document_path=document_path,
            image_count=len(processed_images),
            review_count=len(review_images),
        )

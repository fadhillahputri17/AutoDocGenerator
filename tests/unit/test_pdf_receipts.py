from pathlib import Path

import pymupdf
from docx import Document
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)
from autodocgenerator.services.file_loader import FileLoader
from autodocgenerator.services.image_processor import ImageProcessor


def create_pdf(path: Path, page_count: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()

    for page_number in range(1, page_count + 1):
        page = document.new_page(width=300, height=500)
        page.insert_text((40, 60), f"Nota halaman {page_number}")

    document.save(path)
    document.close()


def test_loader_accepts_pdf_only_inside_nota_real(tmp_path: Path) -> None:
    receipt_pdf = tmp_path / "NOTA REAL" / "Pengajuan Pakan.pdf"
    outside_pdf = tmp_path / "TRANSFER" / "bukan-nota.pdf"
    create_pdf(receipt_pdf, page_count=1)
    create_pdf(outside_pdf, page_count=1)

    loaded = FileLoader().load(tmp_path)

    assert len(loaded) == 1
    assert loaded[0].path == receipt_pdf.resolve()
    assert loaded[0].is_pdf_receipt is True
    assert loaded[0].pdf_title == "Pengajuan Pakan"


def test_pdf_receipt_is_rendered_into_ordered_images(tmp_path: Path) -> None:
    pdf_path = tmp_path / "NOTA REAL" / "Reimburse Sekam.pdf"
    create_pdf(pdf_path, page_count=2)

    source = SourceImage(
        path=pdf_path,
        image_type=DocumentImageType.REAL_RECEIPT,
        pdf_title=pdf_path.stem,
    )

    results = ImageProcessor().process_all(
        [source],
        tmp_path / "output",
    )

    assert len(results) == 2
    assert [item.pdf_page_number for item in results] == [1, 2]
    assert all(item.pdf_page_count == 2 for item in results)
    assert all(item.processed_path is not None for item in results)
    assert all(item.processed_path.exists() for item in results if item.processed_path)
    assert results[0].processed_path.name.startswith("001_")
    assert results[1].processed_path.name.startswith("002_")


def test_pdf_title_is_added_once_above_first_page(tmp_path: Path) -> None:
    first_path = tmp_path / "first.jpg"
    second_path = tmp_path / "second.jpg"
    Image.new("RGB", (600, 900), "white").save(first_path)
    Image.new("RGB", (600, 900), "white").save(second_path)

    pages = [
        SourceImage(
            path=tmp_path / "NOTA REAL" / "Reimburse Sekam.pdf",
            image_type=DocumentImageType.REAL_RECEIPT,
            processed_path=first_path,
            pdf_title="Reimburse Sekam",
            pdf_page_number=1,
            pdf_page_count=2,
        ),
        SourceImage(
            path=tmp_path / "NOTA REAL" / "Reimburse Sekam.pdf",
            image_type=DocumentImageType.REAL_RECEIPT,
            processed_path=second_path,
            pdf_title="Reimburse Sekam",
            pdf_page_number=2,
            pdf_page_count=2,
        ),
    ]

    output = DocumentGenerator(
        settings=DocumentGenerationSettings(
            company_name="PT. TEST",
            bank_name="BCA",
        )
    ).generate(
        pages,
        tmp_path / "output",
    )

    document = Document(output)
    texts = [paragraph.text for paragraph in document.paragraphs]

    assert texts.count("Reimburse Sekam") == 1

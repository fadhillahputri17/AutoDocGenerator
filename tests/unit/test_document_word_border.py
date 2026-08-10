from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)

DRAWINGML_NAMESPACE = (
    "http://schemas.openxmlformats.org/drawingml/2006/main"
)


def _create_image(
    path: Path,
    size: tuple[int, int],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    Image.new(
        "RGB",
        size,
        "white",
    ).save(path)


def test_word_picture_border_is_applied_to_transfer_and_receipt(
    tmp_path: Path,
) -> None:
    transfer_path = tmp_path / "transfer.jpg"
    receipt_path = tmp_path / "nota.png"

    _create_image(
        transfer_path,
        (800, 700),
    )
    _create_image(
        receipt_path,
        (600, 900),
    )

    images = [
        SourceImage(
            path=transfer_path,
            image_type=DocumentImageType.TRANSFER_PROOF,
            processed_path=transfer_path,
        ),
        SourceImage(
            path=receipt_path,
            image_type=DocumentImageType.REAL_RECEIPT,
            processed_path=receipt_path,
        ),
    ]

    output_path = DocumentGenerator(
        settings=DocumentGenerationSettings(
            company_name="PT. TEST INDONESIA",
            bank_name="BCA",
            picture_border_width_pt=1.5,
            picture_border_color_hex="000000",
        )
    ).generate(
        images,
        tmp_path / "output",
        document_date=date(2026, 7, 29),
    )

    with ZipFile(output_path) as archive:
        document_xml = archive.read(
            "word/document.xml"
        )

    root = ElementTree.fromstring(document_xml)
    line_tag = f"{{{DRAWINGML_NAMESPACE}}}ln"
    solid_fill_tag = (
        f"{{{DRAWINGML_NAMESPACE}}}solidFill"
    )
    color_tag = (
        f"{{{DRAWINGML_NAMESPACE}}}srgbClr"
    )

    matching_lines = []

    for line in root.iter(line_tag):
        if line.attrib.get("w") != "19050":
            continue

        solid_fill = line.find(solid_fill_tag)

        if solid_fill is None:
            continue

        color = solid_fill.find(color_tag)

        if (
            color is not None
            and color.attrib.get("val") == "000000"
        ):
            matching_lines.append(line)

    assert len(matching_lines) == 2

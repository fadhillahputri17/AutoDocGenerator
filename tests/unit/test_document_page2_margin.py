from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.document_generator import (
    DocumentGenerationSettings,
    DocumentGenerator,
)

WP_NAMESPACE = (
    "http://schemas.openxmlformats.org/"
    "drawingml/2006/wordprocessingDrawing"
)
EMU_PER_CM = 360_000


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


def test_page_two_transfer_hits_red_17_cm_ruler_target(
    tmp_path: Path,
) -> None:
    images: list[SourceImage] = []

    for index in range(4):
        path = tmp_path / f"transfer_{index + 1}.jpg"
        _create_image(
            path,
            (800, 700),
        )
        images.append(
            SourceImage(
                path=path,
                image_type=DocumentImageType.TRANSFER_PROOF,
                processed_path=path,
            )
        )

    settings = DocumentGenerationSettings(
        company_name="PT. TEST INDONESIA",
        bank_name="BCA",
    )

    output_path = DocumentGenerator(
        settings=settings,
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
    anchor_tag = f"{{{WP_NAMESPACE}}}anchor"
    position_tag = f"{{{WP_NAMESPACE}}}positionH"
    offset_tag = f"{{{WP_NAMESPACE}}}posOffset"
    extent_tag = f"{{{WP_NAMESPACE}}}extent"

    anchors = list(root.iter(anchor_tag))

    assert len(anchors) == 4

    for anchor in anchors[2:]:
        horizontal = anchor.find(position_tag)
        extent = anchor.find(extent_tag)

        assert horizontal is not None
        assert extent is not None

        offset = horizontal.find(offset_tag)

        assert offset is not None
        assert offset.text is not None

        left_page_cm = int(offset.text) / EMU_PER_CM
        width_cm = int(extent.attrib["cx"]) / EMU_PER_CM
        right_page_cm = left_page_cm + width_cm
        right_ruler_cm = (
            right_page_cm
            - settings.page_margin_left_cm
        )

        assert left_page_cm == pytest.approx(
            5.38,
            abs=0.00001,
        )
        assert width_cm == pytest.approx(
            14.16,
            abs=0.00001,
        )
        assert right_page_cm == pytest.approx(
            19.54,
            abs=0.00001,
        )
        assert right_ruler_cm == pytest.approx(
            17.00,
            abs=0.00001,
        )

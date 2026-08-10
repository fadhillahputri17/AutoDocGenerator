from pathlib import Path

import pytest
from PIL import Image

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.exceptions import FileLoadingError
from autodocgenerator.services.file_loader import FileLoader


def create_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (100, 100), color).save(path)


def test_load_classifies_transfer_and_real_receipt(tmp_path: Path) -> None:
    transfer = tmp_path / "TRANSFER" / "transfer.jpg"
    receipt = tmp_path / "NOTA REAL" / "subfolder" / "nota.png"

    create_image(transfer, (255, 255, 255))
    create_image(receipt, (230, 220, 200))

    images = FileLoader().load(tmp_path)

    by_name = {image.filename: image for image in images}

    assert by_name["transfer.jpg"].image_type is DocumentImageType.TRANSFER_PROOF
    assert by_name["nota.png"].image_type is DocumentImageType.REAL_RECEIPT


def test_load_removes_duplicate_content(tmp_path: Path) -> None:
    first = tmp_path / "TRANSFER" / "a.jpg"
    duplicate = tmp_path / "TRANSFER" / "nested" / "b.jpg"

    create_image(first, (10, 20, 30))
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_bytes(first.read_bytes())

    images = FileLoader().load(tmp_path)

    assert len(images) == 1
    assert images[0].path == first.resolve()


def test_load_ignores_unsupported_files(tmp_path: Path) -> None:
    create_image(tmp_path / "TRANSFER" / "valid.jpg", (255, 255, 255))
    (tmp_path / "TRANSFER" / "notes.txt").write_text("not an image", encoding="utf-8")

    images = FileLoader().load(tmp_path)

    assert [image.filename for image in images] == ["valid.jpg"]


def test_load_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileLoadingError):
        FileLoader().load(tmp_path / "missing")


def test_load_rejects_directory_without_supported_images(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("empty", encoding="utf-8")

    with pytest.raises(FileLoadingError):
        FileLoader().load(tmp_path)

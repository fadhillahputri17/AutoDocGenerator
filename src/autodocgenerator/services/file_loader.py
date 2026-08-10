from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.exceptions import FileLoadingError
from autodocgenerator.domain.models import SourceImage


@dataclass(slots=True, frozen=True)
class FileLoaderSettings:
    transfer_folder_name: str = "TRANSFER"
    real_receipt_folder_name: str = "NOTA REAL"
    supported_image_extensions: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
    )
    pdf_extension: str = ".pdf"

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (
            *self.supported_image_extensions,
            self.pdf_extension,
        )


class FileLoader:
    """Load, classify, and deduplicate transfer images and REAL RECEIPT files."""

    def __init__(self, *, settings: FileLoaderSettings | None = None) -> None:
        self._settings = settings or FileLoaderSettings()
        self._normalized_receipt_folder_name = self._normalize_folder_name(
            self._settings.real_receipt_folder_name
        )

    def load(self, input_directory: Path) -> list[SourceImage]:
        root = input_directory.expanduser().resolve()

        if not root.exists() or not root.is_dir():
            raise FileLoadingError(f"Folder input tidak ditemukan: {root}")

        candidates = sorted(
            (
                path
                for path in root.rglob("*")
                if path.is_file() and self._is_supported_candidate(path, root)
            ),
            key=lambda path: (
                len(path.relative_to(root).parts),
                str(path.relative_to(root)).casefold(),
            ),
        )

        if not candidates:
            raise FileLoadingError(
                "Tidak ada gambar atau PDF nota yang didukung di folder "
                f"input: {root}"
            )

        seen_keys: set[str] = set()
        loaded: list[SourceImage] = []

        for path in candidates:
            key = self._deduplication_key(path)

            if key in seen_keys:
                continue

            seen_keys.add(key)
            image_type = self._classify(path, root)
            is_pdf = path.suffix.casefold() == self._settings.pdf_extension.casefold()

            loaded.append(
                SourceImage(
                    path=path.resolve(),
                    image_type=image_type,
                    pdf_title=path.stem if is_pdf else None,
                )
            )

        return loaded

    def _is_supported_candidate(self, path: Path, root: Path) -> bool:
        suffix = path.suffix.casefold()

        if suffix not in {
            extension.casefold()
            for extension in self._settings.supported_extensions
        }:
            return False

        if suffix != self._settings.pdf_extension.casefold():
            return True

        return self._is_in_real_receipt_folder(path, root)

    def _classify(self, path: Path, root: Path) -> DocumentImageType:
        if self._is_in_real_receipt_folder(path, root):
            return DocumentImageType.REAL_RECEIPT

        return DocumentImageType.TRANSFER_PROOF

    def _is_in_real_receipt_folder(self, path: Path, root: Path) -> bool:
        for part in path.relative_to(root).parts[:-1]:
            if self._normalize_folder_name(part) == self._normalized_receipt_folder_name:
                return True

        return False

    @staticmethod
    def _normalize_folder_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    def _deduplication_key(self, path: Path) -> str:
        if path.suffix.casefold() == self._settings.pdf_extension.casefold():
            return f"pdf:{path.resolve()}".casefold()

        return f"image:{self._sha256(path)}"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()

        try:
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise FileLoadingError(f"Gagal membaca file: {path}") from error

        return digest.hexdigest()

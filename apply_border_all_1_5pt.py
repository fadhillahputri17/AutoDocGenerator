from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import ClassVar

import pymupdf
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from pytesseract import Output

from autodocgenerator.domain.exceptions import ImageProcessingError
from autodocgenerator.domain.models import SourceImage


@dataclass(slots=True, frozen=True)
class ImageProcessingSettings:
    """Configuration for transfer cropping, PDF rendering, and borders."""

    border_width_pt: float = 1.5
    output_dpi: int = 96
    jpeg_quality: int = 95
    border_color: str = "black"
    pdf_render_dpi: int = 180

    transfer_initial_top_trim_ratio: float = 0.07
    transfer_initial_bottom_trim_ratio: float = 0.06
    transfer_initial_left_trim_ratio: float = 0.0
    transfer_initial_right_trim_ratio: float = 0.0
    transfer_background_threshold: int = 247
    transfer_saturation_threshold: int = 24
    transfer_min_component_area: int = 120
    transfer_content_padding_px: int = 8
    transfer_extra_top_crop_ratio: float = 0.295
    transfer_square_output: bool = False

    table_header_min_width_ratio: float = 0.48
    table_header_min_height_ratio: float = 0.008
    table_header_max_height_ratio: float = 0.075
    table_header_min_fill_ratio: float = 0.45
    blue_hue_min: int = 85
    blue_hue_max: int = 135
    blue_saturation_min: int = 45
    blue_value_min: int = 65
    horizontal_padding_ratio: float = 0.0
    title_search_height_ratio: float = 0.60
    title_max_gap_from_header_ratio: float = 0.20
    title_row_min_activity_ratio: float = 0.012
    bottom_search_height_ratio: float = 0.85
    row_min_activity_ratio: float = 0.008
    bottom_stop_gap_ratio: float = 0.055

    title_padding_ratio: float = 0.006
    bottom_padding_ratio: float = 0.010
    ocr_page_segmentation_mode: int = 11
    ocr_minimum_word_confidence: float = 0.0
    ocr_fuzzy_match_threshold: float = 0.62

    def __post_init__(self) -> None:
        if self.border_width_pt < 0:
            raise ValueError(
                "border_width_pt must be greater than or equal to zero."
            )

        if self.output_dpi <= 0:
            raise ValueError("output_dpi must be greater than zero.")

        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")

        if self.pdf_render_dpi <= 0:
            raise ValueError("pdf_render_dpi must be greater than zero.")

        ratio_fields = {
            "transfer_initial_top_trim_ratio": (
                self.transfer_initial_top_trim_ratio
            ),
            "transfer_initial_bottom_trim_ratio": (
                self.transfer_initial_bottom_trim_ratio
            ),
            "transfer_initial_left_trim_ratio": (
                self.transfer_initial_left_trim_ratio
            ),
            "transfer_initial_right_trim_ratio": (
                self.transfer_initial_right_trim_ratio
            ),
            "transfer_extra_top_crop_ratio": (
                self.transfer_extra_top_crop_ratio
            ),
            "title_padding_ratio": self.title_padding_ratio,
            "bottom_padding_ratio": self.bottom_padding_ratio,
            "ocr_fuzzy_match_threshold": self.ocr_fuzzy_match_threshold,
        }

        for field_name, value in ratio_fields.items():
            if not 0 <= value < 1:
                raise ValueError(
                    f"{field_name} must be between 0 and less than 1."
                )

        if not 0 <= self.ocr_minimum_word_confidence <= 100:
            raise ValueError(
                "ocr_minimum_word_confidence must be between 0 and 100."
            )

        if self.ocr_page_segmentation_mode < 0:
            raise ValueError(
                "ocr_page_segmentation_mode must not be negative."
            )


@dataclass(slots=True, frozen=True)
class _OCRLine:
    text: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2


class ImageProcessor:
    """
    Prepare transfer proofs and REAL RECEIPT files for Word generation.

    Transfer proof:
    - crop vertically from the line containing "Transfer Dana ...";
    - stop immediately after the line containing "Diotorisasi";
    - keep the full horizontal width;
    - add a 1.5 pt border by default.

    REAL RECEIPT image:
    - never crop, resize, pad, or force a square;
    - preserve the original aspect ratio;
    - add a 1.5 pt border by default.

    REAL RECEIPT PDF:
    - render every page as a lossless PNG;
    - preserve page order and page aspect ratio;
    - never run the transfer crop on rendered pages;
    - add a 1.5 pt border to every rendered page.
    """

    _WORD_NATIVE_EXTENSIONS: ClassVar[frozenset[str]] = frozenset(
        {
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".gif",
            ".tif",
            ".tiff",
            ".webp",
        }
    )

    def __init__(
        self,
        *,
        settings: ImageProcessingSettings | None = None,
    ) -> None:
        self._settings = settings or ImageProcessingSettings()

    def process_all(
        self,
        source_images: list[SourceImage],
        output_directory: Path,
    ) -> list[SourceImage]:
        processed_directory = (
            output_directory.expanduser().resolve() / "processed_images"
        )
        processed_directory.mkdir(parents=True, exist_ok=True)

        results: list[SourceImage] = []
        sequence_number = 1

        for source_image in source_images:
            if source_image.is_pdf_receipt:
                try:
                    pages = self._process_pdf_receipt(
                        source_image=source_image,
                        processed_directory=processed_directory,
                        starting_sequence_number=sequence_number,
                    )
                except ImageProcessingError as error:
                    source_image.requires_review = True
                    source_image.warnings.append(
                        f"Pemrosesan PDF gagal: {error}"
                    )
                    results.append(source_image)
                    sequence_number += 1
                else:
                    results.extend(pages)
                    sequence_number += len(pages)

                continue

            try:
                self.process_single(
                    source_image=source_image,
                    processed_directory=processed_directory,
                    sequence_number=sequence_number,
                )
            except ImageProcessingError as error:
                source_image.requires_review = True
                source_image.warnings.append(
                    f"Pemrosesan gambar gagal: {error}"
                )

            results.append(source_image)
            sequence_number += 1

        return results

    def process_single(
        self,
        *,
        source_image: SourceImage,
        processed_directory: Path,
        sequence_number: int,
    ) -> SourceImage:
        source_path = source_image.path.expanduser().resolve()

        if not source_path.is_file():
            raise ImageProcessingError(
                f"File gambar tidak ditemukan: {source_path}"
            )

        processed_directory = processed_directory.expanduser().resolve()
        processed_directory.mkdir(parents=True, exist_ok=True)

        if source_image.is_real_receipt:
            output_path = self._process_real_receipt_image(
                source_path=source_path,
                processed_directory=processed_directory,
                sequence_number=sequence_number,
            )
            source_image.processed_path = output_path
            return source_image

        output_path = self._build_transfer_output_path(
            source_image=source_image,
            processed_directory=processed_directory,
            sequence_number=sequence_number,
        )

        try:
            with Image.open(source_path) as source:
                prepared = self._prepare_rgb_image(source)
                cropped = self._prepare_transfer_proof(prepared)
                bordered = self._add_border(cropped)
                bordered.save(
                    output_path,
                    format="JPEG",
                    quality=self._settings.jpeg_quality,
                    optimize=True,
                    dpi=(
                        self._settings.output_dpi,
                        self._settings.output_dpi,
                    ),
                )
        except UnidentifiedImageError as error:
            raise ImageProcessingError(
                f"File bukan gambar yang valid: {source_path}"
            ) from error
        except OSError as error:
            raise ImageProcessingError(
                f"Gambar tidak dapat diproses: {source_path}"
            ) from error

        source_image.processed_path = output_path
        return source_image

    def _process_real_receipt_image(
        self,
        *,
        source_path: Path,
        processed_directory: Path,
        sequence_number: int,
    ) -> Path:
        suffix = source_path.suffix.casefold()

        if suffix not in self._WORD_NATIVE_EXTENSIONS:
            raise ImageProcessingError(
                f"Format nota real tidak didukung: {source_path.suffix}"
            )

        safe_stem = self._sanitize_filename(source_path.stem)
        output_path = processed_directory / (
            f"{sequence_number:03d}_{safe_stem}.png"
        )

        try:
            with Image.open(source_path) as source:
                prepared = self._prepare_rgb_image(source)
                bordered = self._add_border(prepared)
                bordered.save(
                    output_path,
                    format="PNG",
                    dpi=(
                        self._settings.output_dpi,
                        self._settings.output_dpi,
                    ),
                )
        except (UnidentifiedImageError, OSError) as error:
            raise ImageProcessingError(
                f"Nota real tidak dapat dibuka: {source_path}"
            ) from error

        return output_path

    def _process_pdf_receipt(
        self,
        *,
        source_image: SourceImage,
        processed_directory: Path,
        starting_sequence_number: int,
    ) -> list[SourceImage]:
        source_path = source_image.path.expanduser().resolve()

        if not source_path.is_file():
            raise ImageProcessingError(
                f"File PDF tidak ditemukan: {source_path}"
            )

        try:
            document = pymupdf.open(source_path)
        except (OSError, RuntimeError, ValueError) as error:
            raise ImageProcessingError(
                f"PDF tidak dapat dibuka: {source_path}"
            ) from error

        try:
            if document.needs_pass:
                raise ImageProcessingError(
                    f"PDF terlindungi kata sandi: {source_path}"
                )

            if document.page_count < 1:
                raise ImageProcessingError(
                    f"PDF tidak mempunyai halaman: {source_path}"
                )

            pages: list[SourceImage] = []
            title = source_image.resolved_pdf_title

            for page_index in range(document.page_count):
                page_number = page_index + 1
                sequence_number = (
                    starting_sequence_number + page_index
                )

                try:
                    page = document.load_page(page_index)
                    pixmap = page.get_pixmap(
                        dpi=self._settings.pdf_render_dpi,
                        alpha=False,
                        colorspace=pymupdf.csRGB,
                    )
                    rendered = Image.frombytes(
                        "RGB",
                        (pixmap.width, pixmap.height),
                        pixmap.samples,
                    )
                    bordered = self._add_border(rendered)
                except (RuntimeError, ValueError) as error:
                    raise ImageProcessingError(
                        "Gagal merender halaman "
                        f"{page_number} dari PDF: {source_path}"
                    ) from error

                output_path = self._build_pdf_output_path(
                    source_image=source_image,
                    processed_directory=processed_directory,
                    sequence_number=sequence_number,
                    page_number=page_number,
                )
                bordered.save(
                    output_path,
                    format="PNG",
                    dpi=(
                        self._settings.pdf_render_dpi,
                        self._settings.pdf_render_dpi,
                    ),
                )

                pages.append(
                    SourceImage(
                        path=source_image.path,
                        image_type=source_image.image_type,
                        transaction_datetime=(
                            source_image.transaction_datetime
                        ),
                        datetime_source=source_image.datetime_source,
                        reference_number=source_image.reference_number,
                        ocr_text=source_image.ocr_text,
                        ocr_confidence=source_image.ocr_confidence,
                        requires_review=source_image.requires_review,
                        warnings=list(source_image.warnings),
                        processed_path=output_path,
                        pdf_title=title,
                        pdf_page_number=page_number,
                        pdf_page_count=document.page_count,
                    )
                )

            return pages
        finally:
            document.close()

    def _prepare_transfer_proof(
        self,
        image: Image.Image,
    ) -> Image.Image:
        cropped = self._adaptive_transfer_crop(image)

        if self._settings.transfer_square_output:
            return self._pad_to_square(cropped)

        return cropped

    def _adaptive_transfer_crop(
        self,
        image: Image.Image,
    ) -> Image.Image:
        crop_box = self._detect_semantic_transaction_box(image)

        if crop_box is None:
            return image.copy()

        left, top, right, bottom = crop_box
        return image.crop((left, top, right, bottom))

    def _detect_semantic_transaction_box(
        self,
        image: Image.Image,
    ) -> tuple[int, int, int, int] | None:
        lines = self._read_ocr_lines(image)

        if not lines:
            return None

        title_candidates = [
            line
            for line in lines
            if self._line_contains_words(
                line,
                ("transfer", "dana"),
            )
        ]

        if not title_candidates:
            return None

        title_line = min(
            title_candidates,
            key=lambda line: line.top,
        )

        authorization_candidates = [
            line
            for line in lines
            if line.top >= title_line.top
            and self._line_contains_any_word(
                line,
                (
                    "diotorisasi",
                    "otorisasi",
                    "authorized",
                ),
            )
        ]

        if authorization_candidates:
            bottom_line = max(
                authorization_candidates,
                key=lambda line: line.bottom,
            )
        else:
            fallback_candidates = [
                line
                for line in lines
                if line.top >= title_line.top
                and (
                    self._line_contains_any_word(
                        line,
                        ("dibuat", "created"),
                    )
                    or re.search(
                        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
                        line.text,
                    )
                )
            ]

            if not fallback_candidates:
                return None

            bottom_line = max(
                fallback_candidates,
                key=lambda line: line.bottom,
            )

        top_padding = max(
            2,
            round(
                image.height
                * self._settings.title_padding_ratio
            ),
        )
        bottom_padding = max(
            2,
            round(
                image.height
                * self._settings.bottom_padding_ratio
            ),
        )

        top = max(
            0,
            title_line.top - top_padding,
        )
        bottom = min(
            image.height,
            bottom_line.bottom + bottom_padding,
        )

        if (
            bottom <= top
            or bottom - top < image.height * 0.08
        ):
            return None

        return (
            0,
            top,
            image.width,
            bottom,
        )

    def _read_ocr_lines(
        self,
        image: Image.Image,
    ) -> list[_OCRLine]:
        config = (
            "--oem 3 "
            f"--psm {self._settings.ocr_page_segmentation_mode}"
        )

        try:
            data = pytesseract.image_to_data(
                image,
                config=config,
                output_type=Output.DICT,
            )
        except (
            pytesseract.TesseractError,
            pytesseract.TesseractNotFoundError,
            OSError,
            RuntimeError,
        ):
            return []

        grouped_indexes: dict[
            tuple[int, int, int, int],
            list[int],
        ] = defaultdict(list)
        text_values = data.get("text", [])

        for index, raw_text in enumerate(text_values):
            text = str(raw_text).strip()

            if not text:
                continue

            confidence = self._parse_confidence(
                data.get("conf", []),
                index,
            )

            if (
                confidence
                < self._settings.ocr_minimum_word_confidence
            ):
                continue

            key = (
                self._safe_data_integer(
                    data,
                    "page_num",
                    index,
                ),
                self._safe_data_integer(
                    data,
                    "block_num",
                    index,
                ),
                self._safe_data_integer(
                    data,
                    "par_num",
                    index,
                ),
                self._safe_data_integer(
                    data,
                    "line_num",
                    index,
                ),
            )
            grouped_indexes[key].append(index)

        lines: list[_OCRLine] = []

        for indexes in grouped_indexes.values():
            words = [
                str(text_values[index]).strip()
                for index in indexes
                if str(text_values[index]).strip()
            ]

            if not words:
                continue

            left = min(
                self._safe_data_integer(
                    data,
                    "left",
                    index,
                )
                for index in indexes
            )
            top = min(
                self._safe_data_integer(
                    data,
                    "top",
                    index,
                )
                for index in indexes
            )
            right = max(
                self._safe_data_integer(
                    data,
                    "left",
                    index,
                )
                + self._safe_data_integer(
                    data,
                    "width",
                    index,
                )
                for index in indexes
            )
            bottom = max(
                self._safe_data_integer(
                    data,
                    "top",
                    index,
                )
                + self._safe_data_integer(
                    data,
                    "height",
                    index,
                )
                for index in indexes
            )

            if left >= right or top >= bottom:
                continue

            lines.append(
                _OCRLine(
                    text=" ".join(words),
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            )

        return sorted(
            lines,
            key=lambda line: (
                line.top,
                line.left,
            ),
        )

    def _line_contains_words(
        self,
        line: _OCRLine,
        required_words: tuple[str, ...],
    ) -> bool:
        return all(
            self._line_contains_any_word(
                line,
                (word,),
            )
            for word in required_words
        )

    def _line_contains_any_word(
        self,
        line: _OCRLine,
        expected_words: tuple[str, ...],
    ) -> bool:
        actual_words = [
            self._normalize_word(word)
            for word in line.text.split()
            if self._normalize_word(word)
        ]

        for expected_word in expected_words:
            normalized_expected = self._normalize_word(
                expected_word
            )

            for actual_word in actual_words:
                if actual_word == normalized_expected:
                    return True

                similarity = SequenceMatcher(
                    None,
                    actual_word,
                    normalized_expected,
                ).ratio()

                if (
                    similarity
                    >= self._settings.ocr_fuzzy_match_threshold
                ):
                    return True

        return False

    @staticmethod
    def _normalize_word(
        value: str,
    ) -> str:
        normalized = value.casefold()
        normalized = normalized.replace("0", "o")
        normalized = normalized.replace("1", "i")
        normalized = normalized.replace("|", "i")
        return re.sub(
            r"[^a-z]",
            "",
            normalized,
        )

    @staticmethod
    def _parse_confidence(
        values: object,
        index: int,
    ) -> float:
        try:
            value = values[index]  # type: ignore[index]
            return float(value)
        except (
            IndexError,
            TypeError,
            ValueError,
        ):
            return -1.0

    @staticmethod
    def _safe_data_integer(
        data: dict[str, list[object]],
        key: str,
        index: int,
    ) -> int:
        values = data.get(key, [])

        try:
            return int(values[index])
        except (
            IndexError,
            TypeError,
            ValueError,
        ):
            return 0

    def _build_transfer_output_path(
        self,
        *,
        source_image: SourceImage,
        processed_directory: Path,
        sequence_number: int,
    ) -> Path:
        safe_stem = self._sanitize_filename(
            source_image.path.stem
        )
        return processed_directory / (
            f"{sequence_number:03d}_{safe_stem}.jpg"
        )

    def _build_pdf_output_path(
        self,
        *,
        source_image: SourceImage,
        processed_directory: Path,
        sequence_number: int,
        page_number: int,
    ) -> Path:
        safe_stem = self._sanitize_filename(
            source_image.path.stem
        )
        return processed_directory / (
            f"{sequence_number:03d}_"
            f"{safe_stem}_page_{page_number:03d}.png"
        )

    def _add_border(
        self,
        image: Image.Image,
    ) -> Image.Image:
        border_width_px = self._border_width_pixels()

        if border_width_px <= 0:
            return image.copy()

        return ImageOps.expand(
            image,
            border=border_width_px,
            fill=self._settings.border_color,
        )

    def _border_width_pixels(self) -> int:
        if self._settings.border_width_pt <= 0:
            return 0

        border_width_px = round(
            self._settings.border_width_pt
            * self._settings.output_dpi
            / 72
        )
        return max(1, border_width_px)

    @staticmethod
    def _prepare_rgb_image(
        image: Image.Image,
    ) -> Image.Image:
        transposed = ImageOps.exif_transpose(image)
        transposed.load()

        if transposed.mode in {"RGBA", "LA"}:
            rgba = transposed.convert("RGBA")
            background = Image.new(
                "RGBA",
                rgba.size,
                "white",
            )
            background.alpha_composite(rgba)
            return background.convert("RGB")

        if (
            transposed.mode == "P"
            and "transparency" in transposed.info
        ):
            rgba = transposed.convert("RGBA")
            background = Image.new(
                "RGBA",
                rgba.size,
                "white",
            )
            background.alpha_composite(rgba)
            return background.convert("RGB")

        return transposed.convert("RGB")

    @staticmethod
    def _sanitize_filename(
        value: str,
    ) -> str:
        sanitized = re.sub(
            r"[^A-Za-z0-9_. -]+",
            "_",
            value,
        ).strip(" .")
        return sanitized[:120] or "image"

    @staticmethod
    def _pad_to_square(
        image: Image.Image,
    ) -> Image.Image:
        size = max(
            image.width,
            image.height,
        )
        canvas = Image.new(
            "RGB",
            (size, size),
            "white",
        )
        left = (size - image.width) // 2
        top = (size - image.height) // 2
        canvas.paste(
            image,
            (left, top),
        )
        return canvas
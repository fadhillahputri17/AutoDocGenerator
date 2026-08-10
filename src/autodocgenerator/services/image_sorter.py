from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from autodocgenerator.domain.models import SourceImage

_DATETIME_PATTERN = re.compile(
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    r"\s+"
    r"(?P<time>\d{1,2}[:.]\d{2}[:.]\d{2})",
    flags=re.IGNORECASE,
)

_BCA_CREATED_LABEL_PATTERN = re.compile(
    r"\b(?:dibuat|created)\b",
    flags=re.IGNORECASE,
)

_BCA_SECTION_PATTERN = re.compile(
    r"pelaksana\s+transaksi",
    flags=re.IGNORECASE,
)

_BRI_TRANSACTION_LABEL_PATTERN = re.compile(
    r"tanggal\s+transaksi",
    flags=re.IGNORECASE,
)

_T = TypeVar(
    "_T",
)


@dataclass(slots=True, frozen=True)
class ImageSortingSettings:
    """
    Configuration for OCR-based image sorting.

    BCA transfer proofs are sorted using the timestamp on the "Dibuat" row.
    The "Diotorisasi" timestamp is deliberately ignored for sorting.

    BRI transfer proofs continue to use the first valid timestamp after
    "Tanggal Transaksi".

    REAL RECEIPT / NOTA REAL images are never OCR-sorted and always remain
    after all transfer proofs.
    """

    bca_created_search_window: int = 260
    bca_section_search_window: int = 1_200
    bri_search_window: int = 500
    add_review_warning_when_datetime_missing: bool = True

    def __post_init__(self) -> None:
        positive_values = {
            "bca_created_search_window":
                self.bca_created_search_window,
            "bca_section_search_window":
                self.bca_section_search_window,
            "bri_search_window":
                self.bri_search_window,
        }

        for field_name, value in positive_values.items():
            if value <= 0:
                raise ValueError(
                    f"{field_name} must be greater than zero."
                )


class ImageSorter:
    """
    Sort source images for document generation.

    Final ordering:
    1. Transfer proofs with a detected OCR datetime, oldest to newest.
    2. Transfer proofs whose datetime could not be detected.
    3. REAL RECEIPT / NOTA REAL images in their existing input order.

    For BCA screenshots, the sort datetime is taken from "Dibuat", not from
    "Diotorisasi". This also overwrites a previously stored authorization
    datetime in ``SourceImage.transaction_datetime`` so the Word title date
    and subsequent processing use the same "Dibuat" value.
    """

    def __init__(
        self,
        *,
        settings: ImageSortingSettings | None = None,
    ) -> None:
        self._settings = settings or ImageSortingSettings()

    def sort(
        self,
        source_images: Sequence[SourceImage],
    ) -> list[SourceImage]:
        """Return images in final document order."""
        dated_transfers: list[
            tuple[
                datetime,
                int,
                SourceImage,
            ]
        ] = []

        undated_transfers: list[
            tuple[
                int,
                SourceImage,
            ]
        ] = []

        real_receipts: list[
            tuple[
                int,
                SourceImage,
            ]
        ] = []

        for original_index, source_image in enumerate(
            source_images
        ):
            if source_image.is_real_receipt:
                real_receipts.append(
                    (
                        original_index,
                        source_image,
                    )
                )

                continue

            sort_datetime = self._resolve_transfer_datetime(
                source_image
            )

            if sort_datetime is None:
                self._mark_missing_datetime_for_review(
                    source_image
                )

                undated_transfers.append(
                    (
                        original_index,
                        source_image,
                    )
                )

                continue

            source_image.transaction_datetime = (
                sort_datetime
            )

            dated_transfers.append(
                (
                    sort_datetime,
                    original_index,
                    source_image,
                )
            )

        dated_transfers.sort(
            key=lambda item: (
                item[
                    0
                ],
                item[
                    1
                ],
            )
        )

        undated_transfers.sort(
            key=lambda item: item[
                0
            ]
        )

        real_receipts.sort(
            key=lambda item: item[
                0
            ]
        )

        return [
            *[
                source_image
                for _, _, source_image
                in dated_transfers
            ],
            *[
                source_image
                for _, source_image
                in undated_transfers
            ],
            *[
                source_image
                for _, source_image
                in real_receipts
            ],
        ]

    def sort_images(
        self,
        source_images: Sequence[SourceImage],
    ) -> list[SourceImage]:
        """
        Compatibility alias for workflows that call ``sort_images``.
        """
        return self.sort(
            source_images
        )

    def __call__(
        self,
        source_images: Sequence[SourceImage],
    ) -> list[SourceImage]:
        """Allow the sorter instance to be called directly."""
        return self.sort(
            source_images
        )

    def _resolve_transfer_datetime(
        self,
        source_image: SourceImage,
    ) -> datetime | None:
        """
        Resolve the datetime used for sorting one transfer proof.

        OCR text is reparsed here so an earlier OCR stage that stored the
        "Diotorisasi" timestamp cannot affect the final BCA order.
        """
        ocr_text = (
            source_image.ocr_text
            or ""
        )

        if not ocr_text.strip():
            return source_image.transaction_datetime

        normalized_text = self._normalize_ocr_text(
            ocr_text
        )

        if self._looks_like_bri(
            normalized_text
        ):
            bri_datetime = self._extract_bri_datetime(
                normalized_text
            )

            if bri_datetime is not None:
                return bri_datetime

        if self._looks_like_bca(
            normalized_text
        ):
            bca_created_datetime = (
                self._extract_bca_created_datetime(
                    normalized_text
                )
            )

            if bca_created_datetime is not None:
                return bca_created_datetime

            # Do not intentionally fall back to the BCA authorization row.
            # An existing datetime is used only when the OCR text does not
            # provide a reliable "Dibuat" value.
            return source_image.transaction_datetime

        generic_datetime = self._extract_first_datetime(
            normalized_text
        )

        if generic_datetime is not None:
            return generic_datetime

        return source_image.transaction_datetime

    def _extract_bca_created_datetime(
        self,
        ocr_text: str,
    ) -> datetime | None:
        """
        Extract the BCA "Dibuat" timestamp.

        Preferred method:
        - find the "Dibuat" label;
        - take the first datetime immediately following that label.

        OCR fallback:
        - find the "Pelaksana Transaksi" section;
        - take the first datetime in that section, because BCA displays
          "Dibuat" before "Diotorisasi".
        """
        for label_match in _BCA_CREATED_LABEL_PATTERN.finditer(
            ocr_text
        ):
            window_start = label_match.start()

            window_end = min(
                len(
                    ocr_text
                ),
                label_match.end()
                + self._settings
                .bca_created_search_window,
            )

            datetime_value = self._extract_first_datetime(
                ocr_text[
                    window_start:window_end
                ]
            )

            if datetime_value is not None:
                return datetime_value

        section_match = _BCA_SECTION_PATTERN.search(
            ocr_text
        )

        if section_match is None:
            return None

        section_end = min(
            len(
                ocr_text
            ),
            section_match.end()
            + self._settings
            .bca_section_search_window,
        )

        section_text = ocr_text[
            section_match.end():section_end
        ]

        section_datetimes = self._extract_all_datetimes(
            section_text
        )

        if not section_datetimes:
            return None

        # The first BCA transaction row is "Dibuat".
        return section_datetimes[
            0
        ]

    def _extract_bri_datetime(
        self,
        ocr_text: str,
    ) -> datetime | None:
        """Extract the first datetime after BRI's 'Tanggal Transaksi'."""
        label_match = _BRI_TRANSACTION_LABEL_PATTERN.search(
            ocr_text
        )

        if label_match is None:
            return None

        window_end = min(
            len(
                ocr_text
            ),
            label_match.end()
            + self._settings.bri_search_window,
        )

        return self._extract_first_datetime(
            ocr_text[
                label_match.start():window_end
            ]
        )

    @staticmethod
    def _looks_like_bca(
        ocr_text: str,
    ) -> bool:
        """Return whether OCR text resembles a BCA transfer proof."""
        return (
            _BCA_SECTION_PATTERN.search(
                ocr_text
            )
            is not None
            or "klikbca" in ocr_text.casefold()
            or "bca virtual account" in ocr_text.casefold()
            or "rekening bca" in ocr_text.casefold()
        )

    @staticmethod
    def _looks_like_bri(
        ocr_text: str,
    ) -> bool:
        """Return whether OCR text resembles a BRI transfer proof."""
        return (
            _BRI_TRANSACTION_LABEL_PATTERN.search(
                ocr_text
            )
            is not None
        )

    @classmethod
    def _extract_first_datetime(
        cls,
        text: str,
    ) -> datetime | None:
        """Return the first valid OCR datetime found in text."""
        for match in _DATETIME_PATTERN.finditer(
            text
        ):
            parsed = cls._parse_datetime_match(
                match
            )

            if parsed is not None:
                return parsed

        return None

    @classmethod
    def _extract_all_datetimes(
        cls,
        text: str,
    ) -> list[datetime]:
        """Return all valid OCR datetimes in their visual/text order."""
        results: list[
            datetime
        ] = []

        for match in _DATETIME_PATTERN.finditer(
            text
        ):
            parsed = cls._parse_datetime_match(
                match
            )

            if parsed is not None:
                results.append(
                    parsed
                )

        return results

    @staticmethod
    def _parse_datetime_match(
        match: re.Match[str],
    ) -> datetime | None:
        """Parse one OCR datetime regex match safely."""
        date_part = match.group(
            "date"
        ).replace(
            "-",
            "/",
        )

        time_part = match.group(
            "time"
        ).replace(
            ".",
            ":",
        )

        raw_value = (
            f"{date_part} "
            f"{time_part}"
        )

        try:
            return datetime.strptime(
                raw_value,
                "%d/%m/%Y %H:%M:%S",
            )
        except ValueError:
            return None

    @staticmethod
    def _normalize_ocr_text(
        text: str,
    ) -> str:
        """
        Normalize OCR separators while retaining row order.

        Newlines are retained because they help preserve the visual sequence
        of "Dibuat" and "Diotorisasi".
        """
        normalized = text.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        normalized = normalized.replace(
            "|",
            " ",
        )

        normalized = re.sub(
            r"[ \t]+",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized,
        )

        return normalized.strip()

    def _mark_missing_datetime_for_review(
        self,
        source_image: SourceImage,
    ) -> None:
        """Mark an undated transfer proof once, without duplicate warnings."""
        if (
            not self._settings
            .add_review_warning_when_datetime_missing
        ):
            return

        source_image.requires_review = True

        warning = (
            "Tanggal/jam transaksi tidak berhasil dibaca. "
            "Untuk BCA, program mencari waktu pada baris Dibuat."
        )

        if warning not in source_image.warnings:
            source_image.warnings.append(
                warning
            )


def sort_images(
    source_images: Sequence[SourceImage],
    *,
    settings: ImageSortingSettings | None = None,
) -> list[SourceImage]:
    """Module-level compatibility function."""
    return ImageSorter(
        settings=settings
    ).sort(
        source_images
    )


def sort_source_images(
    source_images: Iterable[SourceImage],
    *,
    settings: ImageSortingSettings | None = None,
) -> list[SourceImage]:
    """Compatibility function accepting any iterable."""
    return sort_images(
        list(
            source_images
        ),
        settings=settings,
    )

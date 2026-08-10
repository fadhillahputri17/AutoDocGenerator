from datetime import datetime
from pathlib import Path

from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage
from autodocgenerator.services.image_sorter import ImageSorter


def make_transfer(
    filename: str,
    *,
    ocr_text: str,
    stored_datetime: datetime | None = None,
) -> SourceImage:
    """Create one transfer-proof model for sorting tests."""
    return SourceImage(
        path=Path(
            filename
        ),
        image_type=DocumentImageType.TRANSFER_PROOF,
        ocr_text=ocr_text,
        transaction_datetime=stored_datetime,
    )


def make_receipt(
    filename: str,
) -> SourceImage:
    """Create one REAL RECEIPT model."""
    return SourceImage(
        path=Path(
            filename
        ),
        image_type=DocumentImageType.REAL_RECEIPT,
    )


def test_bca_uses_dibuat_instead_of_diotorisasi() -> None:
    image = make_transfer(
        "bca.jpg",
        ocr_text="""
        Pelaksana Transaksi
        User Id Tindakan Tanggal
        VOLVO960 Dibuat 06/07/2026 09:44:42
        VOLVO960 Diotorisasi 06/07/2026 09:58:40
        """,
        stored_datetime=datetime(
            2026,
            7,
            6,
            9,
            58,
            40,
        ),
    )

    result = ImageSorter().sort(
        [
            image,
        ]
    )

    assert result == [
        image,
    ]

    assert image.transaction_datetime == datetime(
        2026,
        7,
        6,
        9,
        44,
        42,
    )


def test_bca_same_authorization_time_is_sorted_by_created_time() -> None:
    later_created = make_transfer(
        "later.jpg",
        ocr_text="""
        Pelaksana Transaksi
        VOLVO960 Dibuat 06/07/2026 17:05:56
        VOLVO960 Diotorisasi 06/07/2026 17:11:22
        """,
        stored_datetime=datetime(
            2026,
            7,
            6,
            17,
            11,
            22,
        ),
    )

    earlier_created = make_transfer(
        "earlier.jpg",
        ocr_text="""
        Pelaksana Transaksi
        VOLVO960 Dibuat 06/07/2026 17:04:05
        VOLVO960 Diotorisasi 06/07/2026 17:11:22
        """,
        stored_datetime=datetime(
            2026,
            7,
            6,
            17,
            11,
            22,
        ),
    )

    result = ImageSorter().sort(
        [
            later_created,
            earlier_created,
        ]
    )

    assert result == [
        earlier_created,
        later_created,
    ]


def test_bca_falls_back_to_first_datetime_in_pelaksana_section() -> None:
    image = make_transfer(
        "bca_ocr_label_missing.jpg",
        ocr_text="""
        Pelaksana Transaksi
        VOLVO960 D1buat 06/07/2026 13:09:47
        VOLVO960 Diotorisasi 06/07/2026 13:10:24
        """,
    )

    ImageSorter().sort(
        [
            image,
        ]
    )

    assert image.transaction_datetime == datetime(
        2026,
        7,
        6,
        13,
        9,
        47,
    )


def test_bri_uses_first_datetime_after_tanggal_transaksi() -> None:
    image = make_transfer(
        "bri.jpg",
        ocr_text="""
        Tanggal Transaksi
        06/07/2026 08:44:25
        Nomor Referensi
        123456789
        """,
    )

    ImageSorter().sort(
        [
            image,
        ]
    )

    assert image.transaction_datetime == datetime(
        2026,
        7,
        6,
        8,
        44,
        25,
    )


def test_undated_transfer_goes_after_dated_transfer() -> None:
    undated = make_transfer(
        "undated.jpg",
        ocr_text="OCR tidak memiliki tanggal",
    )

    dated = make_transfer(
        "dated.jpg",
        ocr_text="""
        Pelaksana Transaksi
        VOLVO960 Dibuat 06/07/2026 10:00:00
        VOLVO960 Diotorisasi 06/07/2026 10:01:00
        """,
    )

    result = ImageSorter().sort(
        [
            undated,
            dated,
        ]
    )

    assert result == [
        dated,
        undated,
    ]

    assert undated.requires_review is True


def test_real_receipts_stay_last_and_keep_input_order() -> None:
    first_receipt = make_receipt(
        "nota_b.jpg"
    )

    second_receipt = make_receipt(
        "nota_a.jpg"
    )

    transfer = make_transfer(
        "transfer.jpg",
        ocr_text="""
        Pelaksana Transaksi
        VOLVO960 Dibuat 06/07/2026 10:00:00
        VOLVO960 Diotorisasi 06/07/2026 10:01:00
        """,
    )

    result = ImageSorter().sort(
        [
            first_receipt,
            transfer,
            second_receipt,
        ]
    )

    assert result == [
        transfer,
        first_receipt,
        second_receipt,
    ]

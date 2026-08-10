from pathlib import Path
from unittest.mock import Mock

from autodocgenerator.application.workflow import AutoDocWorkflow
from autodocgenerator.domain.enums import DocumentImageType
from autodocgenerator.domain.models import SourceImage


def test_workflow_runs_components_in_order(tmp_path: Path) -> None:
    source = SourceImage(
        path=tmp_path / "transfer.jpg",
        image_type=DocumentImageType.TRANSFER_PROOF,
    )

    processed = SourceImage(
        path=source.path,
        image_type=source.image_type,
        processed_path=tmp_path / "processed.jpg",
    )
    processed.processed_path.write_bytes(b"image")

    document_path = tmp_path / "output.docx"
    document_path.write_bytes(b"docx")

    loader = Mock()
    loader.load.return_value = [source]

    ocr = Mock()
    ocr.process_all.return_value = [source]

    sorter = Mock()
    sorter.sort.return_value = [source]

    processor = Mock()
    processor.process_all.return_value = [processed]

    document = Mock()
    document.generate.return_value = document_path

    messages: list[str] = []

    workflow = AutoDocWorkflow(
        file_loader=loader,
        ocr_processor=ocr,
        image_sorter=sorter,
        image_processor=processor,
        document_generator=document,
    )

    result = workflow.run(
        input_directory=tmp_path / "input",
        output_directory=tmp_path / "output",
        progress=messages.append,
    )

    loader.load.assert_called_once()
    ocr.process_all.assert_called_once_with([source])
    sorter.sort.assert_called_once_with([source])
    processor.process_all.assert_called_once()
    document.generate.assert_called_once()

    assert result.document_path == document_path
    assert result.image_count == 1
    assert result.review_count == 0
    assert messages[-1].startswith("Selesai:")


def test_workflow_writes_review_report(tmp_path: Path) -> None:
    source = SourceImage(
        path=tmp_path / "bad.jpg",
        image_type=DocumentImageType.TRANSFER_PROOF,
        requires_review=True,
        warnings=["Tanggal tidak terbaca"],
        processed_path=tmp_path / "processed.jpg",
    )
    source.processed_path.write_bytes(b"image")

    document_path = tmp_path / "document.docx"
    document_path.write_bytes(b"docx")

    loader = Mock(load=Mock(return_value=[source]))
    ocr = Mock(process_all=Mock(return_value=[source]))
    sorter = Mock(sort=Mock(return_value=[source]))
    processor = Mock(process_all=Mock(return_value=[source]))
    document = Mock(generate=Mock(return_value=document_path))

    result = AutoDocWorkflow(
        file_loader=loader,
        ocr_processor=ocr,
        image_sorter=sorter,
        image_processor=processor,
        document_generator=document,
    ).run(
        input_directory=tmp_path / "input",
        output_directory=tmp_path / "output",
    )

    review_text = (result.run_directory / "review" / "review.txt").read_text(
        encoding="utf-8"
    )

    assert result.review_count == 1
    assert "Tanggal tidak terbaca" in review_text

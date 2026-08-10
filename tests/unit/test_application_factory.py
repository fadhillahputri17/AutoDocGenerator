from autodocgenerator.application.factory import (
    ApplicationSettings,
    build_workflow,
)
from autodocgenerator.application.workflow import AutoDocWorkflow


def test_build_workflow_returns_complete_workflow() -> None:
    workflow = build_workflow(
        ApplicationSettings(
            company_name="PT. TEST INDONESIA",
            bank_name="BCA",
        )
    )

    assert isinstance(workflow, AutoDocWorkflow)
    assert workflow._file_loader is not None
    assert workflow._ocr_processor is not None
    assert workflow._image_sorter is not None
    assert workflow._image_processor is not None
    assert workflow._document_generator is not None

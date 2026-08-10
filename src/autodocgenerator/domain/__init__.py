"""Domain objects used throughout AutoDocGenerator."""

from autodocgenerator.domain.enums import DatetimeSource, DocumentImageType
from autodocgenerator.domain.exceptions import (
    AutoDocGeneratorError,
    ConfigurationError,
    DocumentGenerationError,
    FileLoadingError,
    ImageProcessingError,
    OCRProcessingError,
)
from autodocgenerator.domain.models import SourceImage

__all__ = [
    "AutoDocGeneratorError",
    "ConfigurationError",
    "DatetimeSource",
    "DocumentGenerationError",
    "DocumentImageType",
    "FileLoadingError",
    "ImageProcessingError",
    "OCRProcessingError",
    "SourceImage",
]

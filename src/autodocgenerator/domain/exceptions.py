class AutoDocGeneratorError(Exception):
    """Base exception for the application."""


class ConfigurationError(AutoDocGeneratorError):
    """Raised when application configuration is invalid."""


class FileLoadingError(AutoDocGeneratorError):
    """Raised when input files cannot be loaded."""


class OCRProcessingError(AutoDocGeneratorError):
    """Raised when OCR processing fails."""


class ImageProcessingError(AutoDocGeneratorError):
    """Raised when an image cannot be processed safely."""


class DocumentGenerationError(AutoDocGeneratorError):
    """Raised when the Word document cannot be generated."""

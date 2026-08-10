"""
Compatibility wrapper for the image sorter.

The implementation lives in ``image_sorter.py``. This module is retained for
projects that still import from ``autodocgenerator.services.sorter``.
"""

from autodocgenerator.services.image_sorter import (
    ImageSorter,
    ImageSortingSettings,
    sort_images,
    sort_source_images,
)

__all__ = [
    "ImageSorter",
    "ImageSortingSettings",
    "sort_images",
    "sort_source_images",
]

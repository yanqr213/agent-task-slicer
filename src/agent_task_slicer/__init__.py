"""Public API for agent-task-slicer."""

from .config import SlicerConfig, load_config
from .models import AcceptanceCriterion, Document, DocumentSection, SliceResult, TaskPackage
from .slicer import TaskSlicer, slice_file, slice_text

__all__ = [
    "AcceptanceCriterion",
    "Document",
    "DocumentSection",
    "SlicerConfig",
    "SliceResult",
    "TaskPackage",
    "TaskSlicer",
    "load_config",
    "slice_file",
    "slice_text",
]

__version__ = "0.4.0"

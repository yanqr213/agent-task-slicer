"""Domain errors and CLI exit codes."""


class SlicerError(Exception):
    """Base class for recoverable slicer errors."""


class ConfigError(SlicerError):
    """Configuration is invalid."""


class InputError(SlicerError):
    """Input file or text cannot be read or parsed."""


class ExportError(SlicerError):
    """Output cannot be written."""


EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_CONFIG_ERROR = 3
EXIT_NO_TASKS = 4
EXIT_EXPORT_ERROR = 5
EXIT_INTERNAL_ERROR = 70


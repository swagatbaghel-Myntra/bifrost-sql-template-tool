"""Reusable SQL template tooling for Bifrost-style analytics workflows."""

from .client import MockBifrostClient, QueryResult, ReadOnlyQueryError
from .exporter import ExportError, export_rows
from .generator import (
    ParameterValidationError,
    SQLTemplateError,
    SQLTemplateRenderer,
    UnknownTemplateError,
)

__all__ = [
    "ExportError",
    "MockBifrostClient",
    "ParameterValidationError",
    "QueryResult",
    "ReadOnlyQueryError",
    "SQLTemplateError",
    "SQLTemplateRenderer",
    "UnknownTemplateError",
    "export_rows",
]

__version__ = "1.0.0"

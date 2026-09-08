from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


class ExportError(Exception):
    """Raised when query results cannot be exported safely."""


SUPPORTED_FORMATS = {"csv", "json", "parquet"}


def _sanitize_csv_cell(value: Any) -> Any:
    """Reduce spreadsheet-formula injection risk in CSV viewers."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _atomic_write(destination: Path, writer: Callable[[Path], None]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        writer(temporary_path)
        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def export_rows(
    rows: list[dict[str, Any]],
    output_path: str | Path,
    output_format: str,
    *,
    overwrite: bool = False,
) -> Path:
    """Export rows to CSV, JSON, or Parquet using an atomic file replace."""
    output_format = output_format.lower()
    if output_format not in SUPPORTED_FORMATS:
        raise ExportError(
            f"Unsupported format {output_format!r}. Choose csv, json, or parquet."
        )
    if not rows:
        raise ExportError("No rows were returned; no output file was created.")
    if any(not isinstance(row, dict) for row in rows):
        raise ExportError("Every result row must be a dictionary.")

    destination = Path(output_path).expanduser().resolve()
    expected_suffix = f".{output_format}"
    if destination.suffix.lower() != expected_suffix:
        raise ExportError(f"Output filename must end with {expected_suffix}.")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists: {destination}. Use --overwrite to replace it."
        )

    if output_format == "json":
        def write_json(path: Path) -> None:
            with path.open("w", encoding="utf-8") as file:
                json.dump(rows, file, ensure_ascii=False, indent=2, default=str)
                file.write("\n")

        _atomic_write(destination, write_json)

    elif output_format == "csv":
        fieldnames = list(rows[0])
        if any(set(row) != set(fieldnames) for row in rows):
            raise ExportError("All CSV rows must contain the same columns.")

        def write_csv(path: Path) -> None:
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {key: _sanitize_csv_cell(value) for key, value in row.items()}
                    )

        _atomic_write(destination, write_csv)

    else:
        def write_parquet(path: Path) -> None:
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ExportError(
                    "Parquet export requires pyarrow. Run: pip install -r requirements.txt"
                ) from exc
            table = pa.Table.from_pylist(rows)
            pq.write_table(table, path)

        _atomic_write(destination, write_parquet)

    return destination

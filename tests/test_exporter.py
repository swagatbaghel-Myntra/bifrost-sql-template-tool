import csv
import json

import pytest

from bifrost_bridge.exporter import ExportError, export_rows


SAMPLE_ROWS = [
    {"brand": "Brand A", "orders": 10},
    {"brand": "Brand B", "orders": 20},
]


def test_exports_json(tmp_path) -> None:
    destination = export_rows(SAMPLE_ROWS, tmp_path / "result.json", "json")
    assert json.loads(destination.read_text(encoding="utf-8")) == SAMPLE_ROWS


def test_exports_csv(tmp_path) -> None:
    destination = export_rows(SAMPLE_ROWS, tmp_path / "result.csv", "csv")
    with destination.open(encoding="utf-8", newline="") as file:
        assert list(csv.DictReader(file))[0] == {"brand": "Brand A", "orders": "10"}


def test_sanitizes_spreadsheet_formula_cells(tmp_path) -> None:
    destination = export_rows(
        [{"brand": "=HYPERLINK('example')", "orders": 1}],
        tmp_path / "result.csv",
        "csv",
    )
    assert "'=HYPERLINK" in destination.read_text(encoding="utf-8")


def test_refuses_overwrite_by_default(tmp_path) -> None:
    destination = tmp_path / "result.json"
    export_rows(SAMPLE_ROWS, destination, "json")
    with pytest.raises(FileExistsError):
        export_rows(SAMPLE_ROWS, destination, "json")


def test_rejects_empty_results(tmp_path) -> None:
    with pytest.raises(ExportError, match="No rows"):
        export_rows([], tmp_path / "result.json", "json")

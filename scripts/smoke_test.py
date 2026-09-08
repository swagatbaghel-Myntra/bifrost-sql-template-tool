"""Dependency-free end-to-end smoke test for constrained environments."""

import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bifrost_bridge.client import MockBifrostClient
from bifrost_bridge.exporter import export_rows
from bifrost_bridge.generator import SQLTemplateRenderer


def main() -> None:
    renderer = SQLTemplateRenderer()
    sql = renderer.render(
        "sku_performance",
        {
            "start_date": "20260101",
            "end_date": "20260131",
            "brands": ["Brand A", "O'Reilly"],
        },
    )
    assert "'O''Reilly'" in sql

    result = MockBifrostClient().execute(sql, "sku_performance")
    assert len(result.rows) == 2

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        json_path = export_rows(result.rows, root / "result.json", "json")
        csv_path = export_rows(result.rows, root / "result.csv", "csv")
        assert len(json.loads(json_path.read_text(encoding="utf-8"))) == 2
        with csv_path.open(encoding="utf-8", newline="") as file:
            assert len(list(csv.DictReader(file))) == 2

    print("Smoke test passed: render -> mock execute -> JSON/CSV export")


if __name__ == "__main__":
    main()

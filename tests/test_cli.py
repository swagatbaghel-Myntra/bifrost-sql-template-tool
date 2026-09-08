import json

from bifrost_bridge.cli import main


def test_templates_command(capsys) -> None:
    assert main(["templates"]) == 0
    assert "sku_performance" in capsys.readouterr().out


def test_render_command(capsys) -> None:
    parameters = json.dumps(
        {
            "start_date": "20260101",
            "end_date": "20260131",
            "platform": "Android",
        }
    )
    assert main(["render", "user_journey", "--params-json", parameters]) == 0
    assert "platform = 'Android'" in capsys.readouterr().out


def test_run_command_exports_csv(tmp_path, capsys) -> None:
    destination = tmp_path / "result.csv"
    parameters = json.dumps(
        {
            "start_date": "20260101",
            "end_date": "20260131",
            "brands": ["Brand A"],
        }
    )
    code = main(
        [
            "run",
            "sku_performance",
            "--params-json",
            parameters,
            "--format",
            "csv",
            "--output",
            str(destination),
        ]
    )
    assert code == 0
    assert destination.exists()
    assert "Exported 2 rows" in capsys.readouterr().out

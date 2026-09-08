from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .client import MockBifrostClient
from .exporter import ExportError, SUPPORTED_FORMATS, export_rows
from .generator import SQLTemplateError, SQLTemplateRenderer


def _load_parameters(args: argparse.Namespace) -> dict[str, Any]:
    if args.params_json:
        raw = args.params_json
    elif args.params_file:
        try:
            raw = Path(args.params_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Could not read parameter file: {exc}") from exc
    else:
        raise ValueError("Provide either --params-file or --params-json.")

    try:
        parameters = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Parameters are not valid JSON: {exc}") from exc
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be a JSON object.")
    return parameters


def _add_parameter_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--params-file", help="Path to a JSON parameter file.")
    group.add_argument("--params-json", help="Parameters as an inline JSON object.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bifrost-bridge",
        description="Validate, render, and locally test approved SQL templates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("templates", help="List approved SQL templates.")

    render_parser = subparsers.add_parser("render", help="Render SQL without running it.")
    render_parser.add_argument("template", help="Registered template name.")
    _add_parameter_arguments(render_parser)

    run_parser = subparsers.add_parser(
        "run",
        help="Run a template with the local mock client and export the result.",
    )
    run_parser.add_argument("template", help="Registered template name.")
    _add_parameter_arguments(run_parser)
    run_parser.add_argument("--output", required=True, help="Destination output file.")
    run_parser.add_argument(
        "--format",
        required=True,
        choices=sorted(SUPPORTED_FORMATS),
        dest="output_format",
    )
    run_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output file.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    renderer = SQLTemplateRenderer()

    try:
        if args.command == "templates":
            for name, definition in renderer.describe_templates().items():
                parameters = ", ".join(definition.parameters)
                print(f"{name}: {definition.description}")
                print(f"  parameters: {parameters}")
            return 0

        parameters = _load_parameters(args)
        sql = renderer.render(args.template, parameters)

        if args.command == "render":
            print(sql)
            return 0

        client = MockBifrostClient()
        result = client.execute(sql, args.template)
        destination = export_rows(
            result.rows,
            args.output,
            args.output_format,
            overwrite=args.overwrite,
        )
        print(
            f"Exported {len(result.rows)} rows to {destination} "
            f"(query_id={result.query_id})"
        )
        return 0
    except (ExportError, SQLTemplateError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

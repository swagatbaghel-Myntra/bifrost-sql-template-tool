from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

class SQLTemplateError(Exception):
    """Base exception for SQL template errors."""


class UnknownTemplateError(SQLTemplateError):
    """Raised when a requested template is not registered."""


class ParameterValidationError(SQLTemplateError):
    """Raised when template parameters are missing or invalid."""


@dataclass(frozen=True)
class ParameterRule:
    kind: str
    required: bool = True
    choices: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TemplateDefinition:
    filename: str
    description: str
    parameters: dict[str, ParameterRule]


# This registry is the allow-list for runnable templates. A new SQL file does
# not become executable until an employee also adds a definition here.
TEMPLATE_REGISTRY: dict[str, TemplateDefinition] = {
    "sku_performance": TemplateDefinition(
        filename="sku_performance.sql",
        description="Daily SKU, order, and revenue performance by brand.",
        parameters={
            "start_date": ParameterRule(kind="date_key"),
            "end_date": ParameterRule(kind="date_key"),
            "brands": ParameterRule(kind="string_list"),
        },
    ),
    "user_journey": TemplateDefinition(
        filename="user_journey.sql",
        description="Daily event volumes and unique users by platform.",
        parameters={
            "start_date": ParameterRule(kind="date_key"),
            "end_date": ParameterRule(kind="date_key"),
            "platform": ParameterRule(
                kind="choice",
                choices=("Android", "iOS", "Web"),
            ),
        },
    ),
}


def sql_literal(value: Any) -> str:
    """Convert a validated scalar into a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ParameterValidationError(
        f"Unsupported SQL parameter type: {type(value).__name__}"
    )


def sql_list(values: list[Any] | tuple[Any, ...]) -> str:
    """Convert a non-empty collection into escaped SQL literals."""
    if not values:
        raise ParameterValidationError("SQL list parameters cannot be empty.")
    return ", ".join(sql_literal(value) for value in values)


class SQLTemplateRenderer:
    """Validate inputs and render only approved SQL templates."""

    def __init__(self, template_directory: Path | None = None) -> None:
        default_directory = Path(__file__).resolve().parents[1] / "sql_templates"
        self.template_directory = (template_directory or default_directory).resolve()

    def available_templates(self) -> list[str]:
        return sorted(TEMPLATE_REGISTRY)

    def describe_templates(self) -> dict[str, TemplateDefinition]:
        return {name: TEMPLATE_REGISTRY[name] for name in self.available_templates()}

    def render(self, template_name: str, parameters: dict[str, Any]) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", template_name):
            raise UnknownTemplateError(f"Invalid template name: {template_name!r}")

        definition = TEMPLATE_REGISTRY.get(template_name)
        if definition is None:
            choices = ", ".join(self.available_templates())
            raise UnknownTemplateError(
                f"Unknown template {template_name!r}. Available templates: {choices}"
            )

        validated = self._validate_parameters(definition, parameters)
        if (
            "start_date" in validated
            and "end_date" in validated
            and validated["start_date"] > validated["end_date"]
        ):
            raise ParameterValidationError(
                "start_date must be earlier than or equal to end_date."
            )

        template_path = (self.template_directory / definition.filename).resolve()
        if template_path.parent != self.template_directory:
            raise SQLTemplateError("The registered template path is outside sql_templates.")
        try:
            template_source = template_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SQLTemplateError(
                f"Registered template file was not found: {definition.filename}"
            ) from exc
        except OSError as exc:
            raise SQLTemplateError(
                f"Could not read registered template: {definition.filename}"
            ) from exc

        rendered_sql = self._render_placeholders(template_source, validated).strip()
        if not rendered_sql:
            raise SQLTemplateError("The rendered SQL query is empty.")
        return f"{rendered_sql.rstrip(';')};"

    @staticmethod
    def _render_placeholders(template_source: str, parameters: dict[str, Any]) -> str:
        """Render the deliberately small, allow-listed template language.

        Supported forms are {{ value }}, {{ value | sql_literal }}, and
        {{ values | sql_list }}. Arbitrary expressions are rejected.
        """
        token_pattern = re.compile(
            r"{{\s*([a-z][a-z0-9_]*)"
            r"(?:\s*\|\s*(sql_literal|sql_list))?\s*}}"
        )
        all_blocks = re.findall(r"{{.*?}}", template_source, flags=re.DOTALL)
        valid_blocks = [match.group(0) for match in token_pattern.finditer(template_source)]
        if all_blocks != valid_blocks:
            raise SQLTemplateError(
                "Template contains an unsupported expression. Only a parameter name "
                "and the sql_literal or sql_list filters are allowed."
            )

        referenced: set[str] = set()

        def replace(match: re.Match[str]) -> str:
            name, filter_name = match.groups()
            referenced.add(name)
            if name not in parameters:
                raise ParameterValidationError(
                    f"Template references undeclared parameter: {name}"
                )
            value = parameters[name]
            if filter_name == "sql_literal":
                return sql_literal(value)
            if filter_name == "sql_list":
                if not isinstance(value, (list, tuple)):
                    raise ParameterValidationError(f"{name} must be a list.")
                return sql_list(value)
            if isinstance(value, bool):
                return "TRUE" if value else "FALSE"
            if isinstance(value, (int, float)):
                return str(value)
            raise SQLTemplateError(
                f"String or list parameter {name!r} requires an explicit SQL filter."
            )

        rendered = token_pattern.sub(replace, template_source)
        unused = set(parameters) - referenced
        if unused:
            raise SQLTemplateError(
                f"Validated parameters not used by template: {', '.join(sorted(unused))}"
            )
        return rendered

    def _validate_parameters(
        self,
        definition: TemplateDefinition,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(parameters, dict):
            raise ParameterValidationError("Parameters must be a JSON object.")

        expected = set(definition.parameters)
        provided = set(parameters)
        required = {
            name for name, rule in definition.parameters.items() if rule.required
        }
        missing = required - provided
        unknown = provided - expected

        if missing:
            raise ParameterValidationError(
                f"Missing parameters: {', '.join(sorted(missing))}"
            )
        if unknown:
            raise ParameterValidationError(
                f"Unexpected parameters: {', '.join(sorted(unknown))}"
            )

        return {
            name: self._validate_value(name, parameters[name], rule)
            for name, rule in definition.parameters.items()
            if name in parameters
        }

    @staticmethod
    def _validate_value(name: str, value: Any, rule: ParameterRule) -> Any:
        if rule.kind == "date_key":
            value_as_string = str(value)
            if not re.fullmatch(r"\d{8}", value_as_string):
                raise ParameterValidationError(f"{name} must use YYYYMMDD format.")
            try:
                datetime.strptime(value_as_string, "%Y%m%d")
            except ValueError as exc:
                raise ParameterValidationError(
                    f"{name} is not a valid calendar date."
                ) from exc
            return int(value_as_string)

        if rule.kind == "choice":
            if not isinstance(value, str) or value not in (rule.choices or ()):
                allowed = ", ".join(rule.choices or ())
                raise ParameterValidationError(f"{name} must be one of: {allowed}")
            return value

        if rule.kind == "string":
            if not isinstance(value, str) or not value.strip():
                raise ParameterValidationError(f"{name} must be a non-empty string.")
            return value.strip()

        if rule.kind == "positive_integer":
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ParameterValidationError(f"{name} must be a positive integer.")
            return value

        if rule.kind == "string_list":
            if not isinstance(value, (list, tuple)) or not value:
                raise ParameterValidationError(f"{name} must be a non-empty list.")
            normalized: list[str] = []
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise ParameterValidationError(
                        f"Every value in {name} must be a non-empty string."
                    )
                normalized.append(item.strip())
            return normalized

        raise ParameterValidationError(
            f"Unsupported validation rule {rule.kind!r} for {name}."
        )

import pytest

from bifrost_bridge.generator import (
    ParameterValidationError,
    SQLTemplateRenderer,
    UnknownTemplateError,
)


@pytest.fixture
def renderer() -> SQLTemplateRenderer:
    return SQLTemplateRenderer()


def test_lists_registered_templates(renderer: SQLTemplateRenderer) -> None:
    assert renderer.available_templates() == ["sku_performance", "user_journey"]


def test_renders_sku_performance_query(renderer: SQLTemplateRenderer) -> None:
    sql = renderer.render(
        "sku_performance",
        {
            "start_date": "20260101",
            "end_date": "20260131",
            "brands": ["Brand A", "Brand B"],
        },
    )
    assert "BETWEEN 20260101 AND 20260131" in sql
    assert "'Brand A', 'Brand B'" in sql
    assert sql.endswith(";")


def test_escapes_single_quotes(renderer: SQLTemplateRenderer) -> None:
    sql = renderer.render(
        "sku_performance",
        {
            "start_date": "20260101",
            "end_date": "20260131",
            "brands": ["O'Reilly"],
        },
    )
    assert "'O''Reilly'" in sql


def test_rejects_missing_parameter(renderer: SQLTemplateRenderer) -> None:
    with pytest.raises(ParameterValidationError, match="Missing parameters"):
        renderer.render(
            "sku_performance",
            {"start_date": "20260101", "end_date": "20260131"},
        )


def test_rejects_unknown_parameter(renderer: SQLTemplateRenderer) -> None:
    with pytest.raises(ParameterValidationError, match="Unexpected parameters"):
        renderer.render(
            "user_journey",
            {
                "start_date": "20260101",
                "end_date": "20260131",
                "platform": "Android",
                "unsafe_parameter": "value",
            },
        )


def test_rejects_invalid_date_range(renderer: SQLTemplateRenderer) -> None:
    with pytest.raises(ParameterValidationError, match="start_date"):
        renderer.render(
            "user_journey",
            {
                "start_date": "20260201",
                "end_date": "20260101",
                "platform": "iOS",
            },
        )


def test_rejects_path_traversal(renderer: SQLTemplateRenderer) -> None:
    with pytest.raises(UnknownTemplateError):
        renderer.render("../../../unsafe", {})

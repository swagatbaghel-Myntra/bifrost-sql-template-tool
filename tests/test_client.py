import pytest

from bifrost_bridge.client import (
    MockBifrostClient,
    ReadOnlyQueryError,
    validate_read_only_sql,
)


def test_mock_client_returns_deterministic_rows() -> None:
    client = MockBifrostClient()
    first = client.execute("SELECT 1;", "sku_performance")
    second = client.execute("SELECT 1;", "sku_performance")
    assert first.query_id == second.query_id
    assert len(first.rows) == 2


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM example",
        "SELECT * FROM example; DROP TABLE example",
        "UPDATE example SET value = 1",
    ],
)
def test_rejects_write_statements(sql: str) -> None:
    with pytest.raises(ReadOnlyQueryError):
        validate_read_only_sql(sql)


def test_keyword_inside_literal_is_not_treated_as_statement() -> None:
    validate_read_only_sql("SELECT * FROM example WHERE brand = 'DROP'")

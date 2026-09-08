from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


class ReadOnlyQueryError(ValueError):
    """Raised when a query is not read-only."""


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    query_id: str


_DISALLOWED_STATEMENTS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|GRANT|REVOKE|CALL)\b",
    flags=re.IGNORECASE,
)

_LITERALS_AND_COMMENTS = re.compile(
    r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/",
    flags=re.DOTALL,
)


def validate_read_only_sql(sql: str) -> None:
    """Perform a conservative safety check before client execution."""
    normalized = _LITERALS_AND_COMMENTS.sub(" ", sql).strip()
    if not normalized:
        raise ReadOnlyQueryError("The SQL query is empty.")
    if not re.match(r"^(SELECT|WITH)\b", normalized, flags=re.IGNORECASE):
        raise ReadOnlyQueryError("Only SELECT or WITH queries are allowed.")
    if _DISALLOWED_STATEMENTS.search(normalized):
        raise ReadOnlyQueryError("A disallowed SQL statement was detected.")
    without_trailing_semicolon = normalized.rstrip().removesuffix(";").rstrip()
    if ";" in without_trailing_semicolon:
        raise ReadOnlyQueryError("Multiple SQL statements are not allowed.")


class MockBifrostClient:
    """Deterministic local client used until an approved adapter is supplied.

    This class never connects to a database and never transmits SQL.
    """

    def execute(self, sql: str, template_name: str) -> QueryResult:
        validate_read_only_sql(sql)
        query_id = "mock-" + hashlib.sha256(sql.encode("utf-8")).hexdigest()[:12]

        if template_name == "sku_performance":
            rows = [
                {
                    "load_date": 20260101,
                    "brand": "Brand A",
                    "active_skus": 120,
                    "total_orders": 86,
                    "total_revenue": 241900.0,
                },
                {
                    "load_date": 20260101,
                    "brand": "Brand B",
                    "active_skus": 75,
                    "total_orders": 54,
                    "total_revenue": 151200.0,
                },
            ]
        elif template_name == "user_journey":
            rows = [
                {
                    "event_date": 20260101,
                    "platform": "Android",
                    "event_name": "product_view",
                    "event_count": 15420,
                    "unique_users": 9310,
                },
                {
                    "event_date": 20260101,
                    "platform": "Android",
                    "event_name": "add_to_cart",
                    "event_count": 3210,
                    "unique_users": 2540,
                },
            ]
        else:
            rows = []

        columns = tuple(rows[0]) if rows else ()
        return QueryResult(columns=columns, rows=rows, query_id=query_id)

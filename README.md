# Bifrost SQL Template Tool

A small, controlled Python tool for validating, rendering, and testing reusable
analytics SQL templates. It includes a deterministic mock client so employees
can develop workflows locally without database credentials or live data. Its
core execution path uses only the Python standard library.

> **Current integration status:** local mock only. The included
> `MockBifrostClient` does not connect to Bifrost or any other database. An
> approved internal adapter must be implemented before live execution.

## What the tool provides

- Allow-listed SQL templates rather than arbitrary runtime SQL
- Strict validation of required, unknown, date, enum, list, and integer inputs
- Escaped SQL string and list literals
- Read-only query checks before client execution
- CSV, JSON, and Parquet exports
- Atomic output writes and opt-in file overwriting
- Spreadsheet-formula protection for CSV text cells
- Unit tests for rendering, validation, safety, exports, and CLI behavior

## Project structure

```text
bifrost-sql-template-tool/
├── bifrost_bridge/
│   ├── __init__.py
│   ├── cli.py
│   ├── client.py
│   ├── exporter.py
│   └── generator.py
├── examples/
│   ├── sku_performance.parameters.json
│   └── user_journey.parameters.json
├── output/
├── sql_templates/
│   ├── sku_performance.sql
│   └── user_journey.sql
├── tests/
├── .gitignore
├── GITHUB_SETUP.md
├── main.py
├── requirements-dev.txt
├── requirements-parquet.txt
└── requirements.txt
```

## Requirements

- Python 3.10 or newer
- No database credentials are required for mock mode

## Setup

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

The core tool has no third-party runtime dependency. Install the test tools:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

For Parquet export, additionally run:

```bash
python -m pip install -r requirements-parquet.txt
```

Run the test suite:

```bash
python -m pytest -v
```

In a restricted environment where dependencies cannot be downloaded, run the
built-in end-to-end smoke test instead:

```bash
python scripts/smoke_test.py
```

## CLI usage

List the approved templates:

```bash
python main.py templates
```

Render a query without executing it:

```bash
python main.py render sku_performance \
  --params-file examples/sku_performance.parameters.json
```

Run it against the mock client and export CSV:

```bash
python main.py run sku_performance \
  --params-file examples/sku_performance.parameters.json \
  --format csv \
  --output output/sku_performance.csv
```

Export JSON or Parquet by changing both `--format` and the filename extension.
An existing file is protected by default; add `--overwrite` only when replacing
that exact output is intentional.

Inline JSON is also supported:

```bash
python main.py render user_journey \
  --params-json '{"start_date":"20260101","end_date":"20260131","platform":"Android"}'
```

On Windows Command Prompt, prefer `--params-file` to avoid shell-quoting issues.

## How employees add a new SQL template

### 1. Create the SQL file

Create a lowercase snake-case file inside `sql_templates/`, for example:

```text
sql_templates/brand_summary.sql
```

Use the tool's constrained `{{ parameter }}` syntax only for values that have
explicit validation rules:

```sql
SELECT
    brand,
    COUNT(DISTINCT sku_id) AS sku_count
FROM commerce.sku_daily_metrics
WHERE load_date BETWEEN {{ start_date }} AND {{ end_date }}
  AND brand = {{ brand | sql_literal }}
GROUP BY brand
```

Do not use an unfiltered placeholder such as `{{ user_input }}`. Use
`sql_literal` for validated scalar strings and `sql_list` for validated lists.
Numeric date keys and integers can be rendered directly after their registry
rules validate them.

### 2. Register the template

Add an entry to `TEMPLATE_REGISTRY` in `bifrost_bridge/generator.py`:

```python
"brand_summary": TemplateDefinition(
    filename="brand_summary.sql",
    description="SKU count for one brand over a selected period.",
    parameters={
        "start_date": ParameterRule(kind="date_key"),
        "end_date": ParameterRule(kind="date_key"),
        "brand": ParameterRule(kind="string"),
    },
),
```

Supported rule kinds are:

| Rule | Accepted value |
| --- | --- |
| `date_key` | A valid `YYYYMMDD` date |
| `choice` | A string in the rule's `choices` tuple |
| `string` | A non-empty string |
| `string_list` | A non-empty list of non-empty strings |
| `positive_integer` | An integer greater than zero |

For a constrained business dimension, prefer `choice` over unrestricted
`string`. Never accept table names, column names, sort directions, joins, or SQL
fragments as ordinary string parameters. If dynamic identifiers are genuinely
required, implement a fixed allow-list and obtain a security review.

### 3. Add an example parameter file

Create `examples/brand_summary.parameters.json`:

```json
{
  "start_date": "20260101",
  "end_date": "20260131",
  "brand": "Brand A"
}
```

Use fictitious values only. Do not commit employee, customer, vendor, or other
sensitive information.

### 4. Add tests

At minimum, test:

- A valid render
- Every required parameter
- Invalid dates and enum values
- Unexpected parameters
- Quotes inside string values
- The expected aggregation grain and filters

Then run:

```bash
python -m pytest -v
python main.py render brand_summary \
  --params-file examples/brand_summary.parameters.json
```

### 5. Request review

The pull request should be reviewed by both the query owner and a data-platform
reviewer. The reviewer should verify table authorization, query cost, privacy,
aggregation grain, date boundaries, null behavior, and whether the template can
return sensitive or excessively granular data.

## Connecting an approved live client

Keep the renderer and exporter unchanged. Implement a separate client adapter
with the same conceptual interface as:

```python
result = client.execute(sql, template_name)
```

The adapter should obtain credentials through the approved company secret or
identity mechanism—not source code, JSON parameter files, CLI flags, or Git.
Before enabling it, add:

- TLS and approved authentication
- Query timeout and row/byte limits
- Retry rules only for safe transient failures
- Cancellation support
- Audit logging without raw sensitive values
- Access-control and data-classification checks
- Unit tests plus a non-production integration test

The lightweight read-only checker is defense in depth, not a SQL parser and not
a replacement for database permissions. The database identity itself should be
read-only and restricted to approved schemas.

## Security and repository hygiene

- Keep the repository private when it contains internal schema or table names.
- Replace the sample table names before internal use and validate permissions.
- Never commit passwords, tokens, cookies, API keys, query results, or `.env`.
- Run secret scanning and dependency scanning in the repository.
- Store production output in approved access-controlled systems, not Git.
- Treat CSV as a sharing format; JSON and Parquet preserve values without the
  CSV spreadsheet sanitization applied by this tool.

## GitHub setup

See [`GITHUB_SETUP.md`](GITHUB_SETUP.md) for both GitHub CLI and browser-based
repository creation instructions.

## Limitations

- Included tables and result rows are illustrative and fictitious.
- Mock rows demonstrate the export pipeline; they do not prove business impact.
- The tool does not yet submit queries to Bifrost.
- Template files must remain trusted and reviewed. The renderer deliberately
  supports only simple placeholders plus `sql_literal` and `sql_list`; it does
  not execute general template expressions.

## License and ownership

Add the organization-approved license or internal ownership notice before broad
distribution. No open-source license is assumed by this starter project.

"""MCP server that lets Claude query your lakehouse through Trino. (WORKSHOP STUB)

Claude Desktop launches this script and talks to it over stdio using the
Model Context Protocol (MCP). Every function below marked with @mcp.tool()
becomes a tool Claude can call — you are handing the model a tiny, read-only
SQL console for your lakehouse.

    Claude Desktop ──(MCP/stdio)──> this script ──(HTTP)──> Trino ──> Iceberg

YOUR MISSION: two of the three tools are unfinished. Look for the TODO blocks
in describe_table() and run_sql(). The plumbing (run_query, to_markdown,
is_safe_identifier) is already written — you only wire the tools together.
list_tables() is complete, use it as your example.

Test your progress anytime:    python mcp_server/smoke_test.py server.py
Stuck? The finished version lives in server_solution.py — no peeking first!
"""

from __future__ import annotations

import os
import re

from mcp.server.fastmcp import FastMCP
from trino.dbapi import connect

# Defaults match docker-compose.yml. Claude Desktop starts this server OUTSIDE
# your shell, so don't rely on exported variables — defaults must just work.
TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_USER = os.getenv("TRINO_USER", "workshop")
TRINO_CATALOG = os.getenv("TRINO_CATALOG", "iceberg")
TRINO_SCHEMA = os.getenv("TRINO_SCHEMA", "coffee")

MAX_ROWS = 200  # never dump unbounded results into the model's context

# Statements that only READ. The AI gets a query console, not the keys.
READ_ONLY_STARTERS = ("select", "show", "describe", "explain", "with")

mcp = FastMCP("lakehouse")


# ── Plumbing (shared by all tools — already done for you) ────────────────────


def run_query(sql: str) -> tuple[list[str], list[tuple]]:
    """Run ONE statement against Trino and return (column_names, rows)."""
    conn = connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchmany(MAX_ROWS + 1)  # +1 lets us detect "there was more"
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return columns, rows
    finally:
        conn.close()


def to_markdown(columns: list[str], rows: list[tuple]) -> str:
    """Format rows as a markdown table — the shape LLMs read most reliably."""
    if not rows:
        return "(query returned no rows)"
    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]

    def cell(value) -> str:
        return "" if value is None else str(value).replace("|", "\\|")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    if truncated:
        lines.append(f"\n(showing the first {MAX_ROWS} rows — use LIMIT or aggregate)")
    return "\n".join(lines)


def is_safe_identifier(name: str) -> bool:
    """Allow 'lots', 'coffee.lots' or 'iceberg.coffee.lots' — nothing else."""
    return re.fullmatch(r"\w+(\.\w+){0,2}", name) is not None


# ── The three tools Claude can call ──────────────────────────────────────────


@mcp.tool()
def list_tables() -> str:
    """List the tables available in the lakehouse (catalog 'iceberg', schema 'coffee')."""
    columns, rows = run_query("SHOW TABLES")
    return to_markdown(columns, rows)


@mcp.tool()
def describe_table(table: str) -> str:
    """Show the columns and data types of one table.

    Args:
        table: Table name, e.g. 'lots' or 'coffee.farms'.
    """
    # ╔═══════════════════════════════════════════════════════════════════╗
    # ║ TODO(workshop) — Exercise 4: implement describe_table             ║
    # ╠═══════════════════════════════════════════════════════════════════╣
    # ║ 1. Validate `table` with is_safe_identifier(table); if it fails,  ║
    # ║    raise ValueError. (Never trust input — not even from an AI!)   ║
    # ║ 2. Run the SQL  DESCRIBE <table>  using run_query(...).           ║
    # ║ 3. Return the result with to_markdown(columns, rows).             ║
    # ║                                                                   ║
    # ║ Hint: list_tables() above is the same recipe with a fixed query.  ║
    # ╚═══════════════════════════════════════════════════════════════════╝
    raise NotImplementedError("Your turn! Implement describe_table (see TODO above).")


@mcp.tool()
def run_sql(query: str) -> str:
    """Run a read-only SQL query (Trino dialect) against the lakehouse.

    Only SELECT / SHOW / DESCRIBE / EXPLAIN / WITH statements are accepted,
    and results are capped at 200 rows — aggregate or LIMIT anything big.

    Example:
        SELECT f.region, round(avg(l.cupping_score), 2) AS score
        FROM lots l JOIN farms f USING (farm_id)
        GROUP BY f.region ORDER BY score DESC
    """
    # ╔═══════════════════════════════════════════════════════════════════╗
    # ║ TODO(workshop) — Exercise 4: implement run_sql                    ║
    # ╠═══════════════════════════════════════════════════════════════════╣
    # ║ 1. Clean up `query`: strip whitespace and any trailing ';'.       ║
    # ║ 2. Guard rails — raise ValueError unless the statement:           ║
    # ║      a. contains no extra ';' (one statement at a time), and      ║
    # ║      b. starts with one of READ_ONLY_STARTERS (case-insensitive). ║
    # ║    Bonus: also reject "EXPLAIN ANALYZE" (it EXECUTES the query!). ║
    # ║ 3. Run it with run_query(...) and return to_markdown(...).        ║
    # ║                                                                   ║
    # ║ Why the guard rails? This tool hands an AI direct SQL access —    ║
    # ║ read-only-by-construction beats read-only-by-politeness.          ║
    # ╚═══════════════════════════════════════════════════════════════════╝
    raise NotImplementedError("Your turn! Implement run_sql (see TODO above).")


if __name__ == "__main__":
    # stdio transport: Claude Desktop launches this process and pipes JSON-RPC
    # through stdin/stdout. That's also why print() is forbidden in this file —
    # any stray text on stdout would corrupt the protocol stream.
    mcp.run(transport="stdio")

"""Create and load the workshop's Iceberg tables — pure Python, no Spark.

What happens when you run this:
  1. Connect to Nessie's Iceberg REST catalog (branch: main).
  2. Create the `coffee` namespace (think: a database/schema).
  3. (Re)create two Iceberg tables — coffee.farms and coffee.lots — and load
     them from the CSVs bundled in data/. PyIceberg writes the Parquet files
     straight into MinIO; Nessie records the table metadata.

Safe to re-run anytime: it drops and reloads the demo tables, so you always
get the same fresh data back (handy after experimenting in the exercises).

Run it:   make seed      — or —      python seed/seed_data.py
"""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pa_csv
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Defaults match docker-compose.yml; the env vars only matter if you changed
# ports/credentials in .env (run via `make seed` to pick those up).
NESSIE_URI = os.getenv(
    "NESSIE_URI", f"http://localhost:{os.getenv('NESSIE_PORT', '19120')}/iceberg/main"
)
MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT", f"http://localhost:{os.getenv('MINIO_PORT', '9000')}"
)
MINIO_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

NAMESPACE = "coffee"

# Explicit schemas — with Iceberg you DESIGN tables, you don't let a CSV
# reader guess them. (date32 = a calendar date, no timezone drama.)
FARMS_SCHEMA = pa.schema(
    [
        pa.field("farm_id", pa.string()),
        pa.field("name", pa.string()),
        pa.field("municipality", pa.string()),
        pa.field("region", pa.string()),
        pa.field("altitude_m", pa.int32()),
        pa.field("hectares", pa.float64()),
        pa.field("founded_year", pa.int32()),
    ]
)
LOTS_SCHEMA = pa.schema(
    [
        pa.field("lot_id", pa.string()),
        pa.field("farm_id", pa.string()),
        pa.field("variety", pa.string()),
        pa.field("process", pa.string()),
        pa.field("harvest_date", pa.date32()),
        pa.field("green_kg", pa.int32()),
        pa.field("cupping_score", pa.float64()),
        pa.field("price_usd_per_kg", pa.float64()),
    ]
)


def check_stack_is_up() -> None:
    """Fail fast with a friendly message instead of a long traceback."""
    config_url = f"{NESSIE_URI.rstrip('/')}/v1/config"
    try:
        urllib.request.urlopen(config_url, timeout=5)
    except OSError:
        print(f"Could not reach the Nessie catalog at {config_url}")
        print("Is the stack running? Start it with:  make up")
        sys.exit(1)


def read_csv(path: Path, schema: pa.Schema) -> pa.Table:
    """Read a bundled CSV, enforcing our column types instead of inferring."""
    table = pa_csv.read_csv(
        path,
        convert_options=pa_csv.ConvertOptions(
            column_types={field.name: field.type for field in schema}
        ),
    )
    return table.select(schema.names).cast(schema)


def recreate_table(catalog, name: str, schema: pa.Schema, csv_file: str) -> None:
    identifier = f"{NAMESPACE}.{name}"
    try:
        catalog.drop_table(identifier)
        print(f"  - {identifier}: dropped previous version")
    except NoSuchTableError:
        pass
    table = catalog.create_table(identifier, schema=schema)
    data = read_csv(DATA_DIR / csv_file, schema)
    table.append(data)
    print(f"  - {identifier}: created and loaded {data.num_rows} rows")


def main() -> None:
    print(f"Connecting to the Nessie catalog at {NESSIE_URI} ...")
    check_stack_is_up()

    catalog = load_catalog(
        "lakehouse",
        **{
            "type": "rest",
            "uri": NESSIE_URI,
            # PyIceberg writes Parquet files directly to MinIO:
            "s3.endpoint": MINIO_ENDPOINT,
            "s3.access-key-id": MINIO_USER,
            "s3.secret-access-key": MINIO_PASSWORD,
            "s3.region": "us-east-1",
        },
    )

    catalog.create_namespace_if_not_exists(NAMESPACE)
    print(f"Namespace '{NAMESPACE}' is ready.")

    recreate_table(catalog, "farms", FARMS_SCHEMA, "farms.csv")
    recreate_table(catalog, "lots", LOTS_SCHEMA, "lots.csv")

    print(
        "\nDone! Your lakehouse has data. Try it out:\n\n"
        "  SQL shell:      make trino\n"
        "                  then:  SELECT count(*) FROM iceberg.coffee.lots;\n"
        f"  Parquet files:  http://localhost:{os.getenv('MINIO_CONSOLE_PORT', '9001')}"
        "  (bucket 'warehouse', login minioadmin/minioadmin)\n"
        f"  Catalog UI:     http://localhost:{os.getenv('NESSIE_PORT', '19120')}"
        "  (every table change is a commit on 'main')\n"
    )


if __name__ == "__main__":
    main()

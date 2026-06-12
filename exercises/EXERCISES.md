# Workshop Exercises — From S3 to AI Agent

> 🇪🇸 Los ejercicios están en inglés (como el código), pero las consultas SQL y
> los comandos son iguales en cualquier idioma — y en el Ejercicio 4 puedes
> hablarle a Claude en español. ¡Pide ayuda cuando quieras!

**Before you start:** the stack is up (`make up`) and seeded (`make seed`).
Open a SQL shell with `make trino` (exit with `Ctrl+D`). In that shell,
table names need the full path the first time: `iceberg.coffee.lots`.

The dataset: **48 coffee farms** (fincas) across 12 Colombian regions and
**360 lots** (a *lot* is one batch of green coffee from one farm) with variety,
process, harvest date, weight, cupping score (quality, 0–100) and price.

---

## Exercise 0 — Know your lakehouse (10 min)

You just started a complete lakehouse. Meet the three pieces:

1. **MinIO (the storage)** → <http://localhost:9001> (user/pass: `minioadmin`/`minioadmin`).
   Browse the `warehouse` bucket. After seeding you'll find a folder per table
   containing **Parquet data files** and **JSON/Avro metadata** — a lakehouse
   is "just files" plus a catalog that gives them meaning.
2. **Nessie (the catalog)** → <http://localhost:19120>.
   It tracks which tables exist and every change made to them — like Git for
   your data warehouse. Find the `main` branch and its commit log: the seed
   you just ran shows up as commits!
3. **Trino (the engine)** → <http://localhost:8080> (log in with any name).
   It turns SQL into reads/writes against those Parquet files.

*Question to discuss:* which AWS service does each one replace?

---

## Exercise 1 — First queries (15 min)

In `make trino`, get a feel for the data:

```sql
-- How much data do we have?
SELECT count(*) FROM iceberg.coffee.lots;

-- Make 'coffee' the default schema so table names get shorter:
USE iceberg.coffee;

-- Which region grows the best coffee? (the eternal Colombian debate)
SELECT f.region,
       round(avg(l.cupping_score), 2) AS avg_score,
       count(*)                       AS lots
FROM lots l
JOIN farms f USING (farm_id)
GROUP BY f.region
ORDER BY avg_score DESC;

-- Does altitude pay? Price and quality by altitude band:
SELECT round(f.altitude_m, -2)            AS altitude_band,
       round(avg(l.price_usd_per_kg), 2)  AS avg_price,
       round(avg(l.cupping_score), 2)     AS avg_score
FROM lots l
JOIN farms f USING (farm_id)
GROUP BY 1
ORDER BY 1;

-- Harvest seasonality — Colombia has TWO harvests (main + "mitaca"):
SELECT month(harvest_date) AS month, sum(green_kg) AS kg
FROM lots
GROUP BY 1
ORDER BY 1;
```

**Your turn:**
- Top 5 most expensive lots — which variety dominates? (spoiler: Geisha)
- Average lot size in kg per process (`washed`, `honey`, `natural`, `anaerobic`).
- Which *municipality* (not region) has the highest average cupping score?

---

## Exercise 2 — Look under the hood (15 min)

Iceberg tables are self-describing. Trino exposes their internals as
`$metadata` tables:

```sql
USE iceberg.coffee;

-- The snapshot behind the table right now:
SELECT snapshot_id, committed_at, operation, summary['total-records'] AS records
FROM "lots$snapshots";

-- The actual Parquet files, with row counts and sizes:
SELECT file_path, record_count, file_size_in_bytes
FROM "lots$files";
```

Now go back to the MinIO console and find those exact files under
`warehouse/coffee/lots_*/`. **That's the whole trick:** open Parquet files in
object storage + metadata that turns them into a transactional table.

> 🧭 One Nessie twist: `"lots$snapshots"` shows exactly **one** snapshot — the
> one matching the current Nessie commit. The full history doesn't live inside
> the table here; it lives in **Nessie's commit log** (check the UI — you'll
> use it to time-travel in Exercise 3).

---

## Exercise 3 — Iceberg + Nessie superpowers (20 min)

### 3a. Save a checkpoint, then write

Every change lands as a Nessie commit, so first grab the current commit hash —
your "save point". Copy the full hash from the Nessie UI, or:

```bash
curl -s http://localhost:19120/api/v2/trees/main | python3 -c "import sys,json; print(json.load(sys.stdin)['reference']['hash'])"
```

Now sell one legendary lot:

```sql
-- Writes are transactions:
INSERT INTO lots VALUES
  ('L9999', 'F001', 'Geisha', 'anaerobic', DATE '2025-12-24', 30, 94.25, 75.00);

SELECT count(*) FROM lots;   -- 361 now
```

### 3b. Time travel — through Nessie

Put the saved hash (the **full** 64-character one) **inside the table name**:

```sql
-- The table as it was at your checkpoint:
SELECT count(*) FROM "lots#<paste-your-full-hash-here>";   -- 360. The past!

-- Or travel by timestamp (UTC, ISO format):
SELECT count(*) FROM "lots#2026-06-15T14:00:00Z";
```

> Why not Iceberg's classic `FOR VERSION AS OF`? Nessie serves exactly one
> snapshot per commit (that's how it keeps *cross-table* consistency), so time
> travel uses Nessie references instead — and they work across your **whole
> catalog**, not just one table.

### 3c. Schema evolution without rewriting data

```sql
ALTER TABLE lots ADD COLUMN organic boolean;

SELECT lot_id, organic FROM lots LIMIT 5;   -- existing rows: NULL, zero rewrite
UPDATE lots SET organic = true WHERE process = 'anaerobic';
```

Check Nessie's UI again — the INSERT, the ALTER and the UPDATE are each a
**commit** on `main`.

> 🔁 Made a mess? `make seed` resets both tables to the original 360 rows.
> Fun fact: the old Parquet files stay behind in MinIO as orphans — exactly
> why real lakehouses run maintenance jobs (snapshot expiry, orphan cleanup).

---

## Exercise 4 — Give your lakehouse to an AI agent (30 min)

Time to finish the MCP server. Open `mcp_server/server.py`: `list_tables()`
works, but `describe_table()` and `run_sql()` are TODO stubs — implement them
following the boxes in the code (the plumbing functions are already written).

Test without touching Claude:

```bash
python mcp_server/smoke_test.py server.py
```

When it passes, connect **your** server to Claude Desktop (README → "Connect
Claude Desktop", using `server.py` instead of `server_solution.py`), restart
Claude Desktop fully, and look for the `lakehouse` tools in the chat.

Now interrogate your lakehouse in natural language — Spanish works great:

- *"¿Qué tablas hay en mi lakehouse y qué columnas tienen?"*
- *"¿Cuál región produce el mejor café? Muéstrame el top 5 con puntaje."*
- *"¿Se paga más por el café cultivado a mayor altitud? Analiza por rangos."*
- *"Find anomalies: lots whose price looks too high or too low for their score."*

Watch the tool calls Claude makes (expand them with the ▸ chevron). Notice how
it first explores the schema, then writes SQL — you built the API that makes
that possible.

**Hardening ideas (discussion):** what stops `run_sql` from deleting data?
Try asking Claude to `DROP TABLE lots` and watch your guard rail catch it.

---

## Exercise 5 (stretch) — Branch your data like Git

Nessie can branch the **whole catalog**. Create a branch, point a second Trino
catalog at it, and experiment without touching `main`:

```bash
# 1. Create branch 'experiments' from main (Nessie REST API v2):
HASH=$(curl -s http://localhost:19120/api/v2/trees/main | python3 -c "import sys,json; print(json.load(sys.stdin)['reference']['hash'])")
curl -s -X POST "http://localhost:19120/api/v2/trees?name=experiments&type=BRANCH" \
     -H "Content-Type: application/json" \
     -d "{\"type\": \"BRANCH\", \"name\": \"main\", \"hash\": \"$HASH\"}"

# 2. A second Trino catalog pinned to the branch (note the URI suffix), then
#    restart Trino to pick it up (~30s):
sed 's|/iceberg/main|/iceberg/experiments|' trino/catalog/iceberg.properties \
  > trino/catalog/iceberg_experiments.properties
docker compose restart trino
```

```sql
-- 3. Write on the branch (explicit columns, in case you added 'organic'):
INSERT INTO iceberg_experiments.coffee.lots
  (lot_id, farm_id, variety, process, harvest_date, green_kg, cupping_score, price_usd_per_kg)
VALUES ('L8888', 'F002', 'Castillo', 'washed', DATE '2026-01-15', 500, 83.00, 6.10);

-- 4. The branch moved; main didn't:
SELECT count(*) FROM iceberg_experiments.coffee.lots;   -- one more...
SELECT count(*) FROM iceberg.coffee.lots;               -- ...than main
```

Browse both branches in the Nessie UI. This is "dev/prod environments for your
data" — without copying a single Parquet file. (To clean up: delete
`trino/catalog/iceberg_experiments.properties` and restart Trino again.)

> ⚠️ Remember: the workshop catalog runs IN-MEMORY, so branches and tables
> disappear whenever the Nessie container restarts. `make seed` rebuilds main
> in seconds.

---

## Where to go next

- Partitioning: recreate `lots` partitioned by region or month
  (`WITH (partitioning = ARRAY['region'])`) and compare `"lots$files"`.
- Table maintenance: `ALTER TABLE lots EXECUTE optimize` and snapshot expiry.
- Swap the seed CSVs for your own data — the pattern doesn't change.
- Production-ify: Nessie backed by a real database, MinIO with TLS and
  versioning, more Trino workers… same open standards, no rewrite.

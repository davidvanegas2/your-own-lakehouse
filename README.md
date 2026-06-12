# From S3 to AI Agent: Your First Queryable Lakehouse ☕

A 2-hour hands-on workshop (PyCon Colombia): build a **complete data lakehouse
on your laptop** — object storage, Iceberg tables, a Git-like catalog, a SQL
engine — and then hand it to an **AI agent** through MCP.

**100% local · 100% open source · zero cloud accounts · zero credit cards.**

[🇬🇧 English](#-english) · [🇪🇸 Español](#-español)

```
 Claude Desktop ──(MCP, stdio)──> mcp_server/server.py ─┐
 you            ──(SQL shell)──────────────────────────> Trino  :8080   ("Athena")
                                                          │
                                            Iceberg REST  │  which tables exist?
                                                          ▼
 seed/seed_data.py (PyIceberg) ──(Iceberg REST)────────> Nessie :19120  ("Glue", but with Git branches)
            │                                             │
            │ writes Parquet                              │ s3://warehouse/...
            ▼                                             ▼
            └──────────────────────────────────────────> MinIO  :9000   ("S3")  · console :9001
```

| In the cloud (AWS)   | On your laptop (this repo)      | Role                            |
| -------------------- | ------------------------------- | ------------------------------- |
| S3                   | **MinIO**                       | object storage (Parquet files)  |
| Glue Data Catalog    | **Nessie** (Iceberg REST)       | catalog — *with Git branching*  |
| Athena               | **Trino**                       | SQL query engine                |
| Glue ETL / EMR Spark | **PyIceberg** (pure Python)     | create + load tables            |
| Bedrock agent        | **Claude Desktop + MCP server** | AI agent that queries your data |

---

## 🇬🇧 English

### Prerequisites

- **Docker Desktop** (or Docker Engine with Compose **v2** — the `docker compose` command, with a space)
- **8 GB RAM** minimum and **10 GB free disk**
- **Python 3.11+** (3.10–3.13 work)
- **Claude Desktop** (free account is fine) for the AI-agent part — macOS or Windows.
  No Linux build exists; on Linux you can still do everything and verify the MCP
  server with `make smoke`.
- Basic SQL and a terminal. `make` is convenient but optional (every target's
  raw command is in the [no-make table](#no-make-no-problem)).

### ⚠️ Before the workshop — do this at home, on good WiFi

Conference WiFi will not download **≈1.5 GB** of images (≈3.8 GB on disk) for
everyone at once. Please pre-pull:

```bash
git clone <this-repo> && cd your-own-lakehouse
docker compose pull          # ≈1.5 GB — grab a coffee
```

Optional but recommended (saves 2 minutes at the workshop):

```bash
make venv                    # or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Quickstart — the happy path

```bash
make up        # = docker compose up -d --wait     (cold start ≈ 20–60 s)
make health    # one-line status check — expect three OKs
make seed      # creates + loads the Iceberg tables (48 farms, 360 coffee lots)
make trino     # opens a SQL shell. Try:
```

```sql
SELECT f.region, round(avg(l.cupping_score), 2) AS score
FROM iceberg.coffee.lots l JOIN iceberg.coffee.farms f USING (farm_id)
GROUP BY f.region ORDER BY score DESC;
```

If that returns Colombian coffee regions ranked by quality — **your lakehouse
is alive.** Continue with [exercises/EXERCISES.md](exercises/EXERCISES.md).

#### Your three services

| Service              | URL                      | Credentials                  |
| -------------------- | ------------------------ | ---------------------------- |
| MinIO console        | <http://localhost:9001>  | `minioadmin` / `minioadmin`  |
| Nessie UI (catalog)  | <http://localhost:19120> | none                         |
| Trino UI             | <http://localhost:8080>  | any username, no password    |

> ♻️ The catalog runs **in-memory** on purpose (one less container): restarting
> the stack empties it. `make seed` rebuilds everything in seconds — it's also
> your "reset button" after experiments. (`make down` stops the stack;
> `make clean` also deletes the MinIO data.)

### Connect Claude Desktop (the AI-agent part)

The MCP server lives in [`mcp_server/`](mcp_server/): `server_solution.py`
works out of the box; `server.py` is the version **you** complete in
Exercise 4. It exposes three tools — `list_tables`, `describe_table`,
`run_sql` (read-only, capped at 200 rows) — and talks to Trino at
`localhost:8080`.

**Step 0 — prove the server works, without Claude:**

```bash
make smoke     # = .venv/bin/python mcp_server/smoke_test.py
```

**Option A — manual config (recommended, always works).**
Open the config file (Claude Desktop → Settings → Developer → Edit Config):

| OS      | Config file                                                     |
| ------- | --------------------------------------------------------------- |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                    |

Paste (replace `/ABS/PATH/TO` with your real absolute path — run `pwd` in the
repo to get it; `~` does not work here):

```json
{
  "mcpServers": {
    "lakehouse": {
      "command": "/ABS/PATH/TO/your-own-lakehouse/.venv/bin/python",
      "args": ["/ABS/PATH/TO/your-own-lakehouse/mcp_server/server_solution.py"]
    }
  }
}
```

On Windows use double backslashes and the Scripts folder:

```json
{
  "mcpServers": {
    "lakehouse": {
      "command": "C:\\ABS\\PATH\\TO\\your-own-lakehouse\\.venv\\Scripts\\python.exe",
      "args": ["C:\\ABS\\PATH\\TO\\your-own-lakehouse\\mcp_server\\server_solution.py"]
    }
  }
}
```

Then **fully quit Claude Desktop** (on Windows: quit from the system tray, not
just the window) and reopen it. The `lakehouse` tools appear in the chat's
tools menu. Ask: *"What tables are in my lakehouse, and which coffee region
scores best?"*

**Option B — `mcp install` (if you use [uv](https://docs.astral.sh/uv/)).**
The official MCP CLI writes the config entry for you — note the generated
entry launches the server through `uv`, so uv must stay installed:

```bash
uv run mcp install mcp_server/server_solution.py --name lakehouse
```

### Workshop flow

[exercises/EXERCISES.md](exercises/EXERCISES.md): tour the stack → SQL on
Iceberg → metadata, **time travel & schema evolution** → finish the MCP server
and connect Claude → (stretch) **branch your data like Git** with Nessie.

### Troubleshooting

| Symptom | Fix |
| ------- | --- |
| **A port is already in use** (8080 is a classic) | `cp .env.example .env`, change the port(s), `make up` again. `make seed`/`make health` read `.env` automatically. If you changed `TRINO_PORT`, also add `"env": {"TRINO_PORT": "<port>"}` to the Claude config entry. |
| **`docker: command not found` / daemon not running** | Install/start Docker Desktop. Needs Compose v2 (`docker compose version`). |
| **Image pull is slow or fails** (conference WiFi…) | Run `docker compose pull` at home beforehand. Pulls resume if interrupted; check you have 10 GB free. |
| **S3-style errors**: `NoSuchBucket`, `SignatureDoesNotMatch`, connection refused on 9000 | The `warehouse` bucket is auto-created — check `docker compose logs minio-init`. MinIO needs path-style S3 access and explicit endpoints; both are pre-configured everywhere. If you changed credentials in `.env`, mirror them in `trino/catalog/iceberg.properties`. |
| **`Table 'iceberg.coffee.lots' does not exist`** after a restart | Expected: the catalog is in-memory. Run `make seed`. |
| **Claude Desktop doesn't show the tools** | Paths in the JSON must be **absolute** (no `~`); Windows needs `\\` and `.venv\Scripts\python.exe`. Fully quit Claude (tray icon!) and reopen. Logs: macOS `~/Library/Logs/Claude/mcp*.log`, Windows `%APPDATA%\Claude\logs`. The stack must be up — Claude launches the server, but Trino answers the queries. |
| **Claude's tool calls error out** | `make health`, then `make smoke`. If smoke passes, the problem is the Claude config, not the server. |
| **First query takes ~seconds** | JVM warm-up. The second one is fast. |
| **Apple Silicon?** | All images are multi-arch (arm64 + amd64). Nothing to do. |

#### No make? No problem

| `make` target | Raw command |
| ------------- | ----------- |
| `make up`     | `docker compose up -d --wait` |
| `make health` | `docker compose ps` |
| `make venv`   | `python3 -m venv .venv` then `.venv/bin/pip install -r requirements.txt` (Windows: `.venv\Scripts\pip install -r requirements.txt`) |
| `make seed`   | `.venv/bin/python seed/seed_data.py` (Windows: `.venv\Scripts\python seed\seed_data.py`) |
| `make trino`  | `docker exec -it trino trino` |
| `make smoke`  | `.venv/bin/python mcp_server/smoke_test.py` |
| `make down`   | `docker compose down` |
| `make clean`  | `docker compose down -v` |

### Pinned versions (verified 2026-06-11)

| Component | Version |
| --------- | ------- |
| MinIO | `minio/minio:RELEASE.2025-09-07T16-13-09Z` (+ `mc RELEASE.2025-08-13T08-35-41Z`) |
| Nessie | `ghcr.io/projectnessie/nessie:0.107.9` |
| Trino | `trinodb/trino:481` |
| PyIceberg | `0.11.1` (+ pyarrow 24.0.0, s3fs 2026.4.0) |
| MCP SDK | `mcp[cli] 1.27.2` |
| Trino Python client | `0.337.0` |

### Design notes (why it's built this way)

- **Iceberg REST catalog, not Trino's native Nessie connector** — REST is the
  standard, engine-neutral protocol; the same endpoint serves Trino *and*
  PyIceberg.
- **Nessie quirk worth knowing:** it serves exactly **one Iceberg snapshot per
  commit** (that's how it keeps cross-table consistency), so classic
  `FOR VERSION AS OF` time travel doesn't apply — you time-travel through
  Nessie commits instead: `SELECT … FROM "lots#<commit-hash-or-utc-timestamp>"`.
  Exercise 3 teaches exactly this.
- **`pyiceberg[s3fs]`** — Nessie's REST responses tell PyIceberg to use its
  fsspec FileIO (`py-io-impl`), which is backed by s3fs. Without it the seed
  fails with `ModuleNotFoundError: s3fs`.
- **Static MinIO credentials everywhere; Nessie request-signing disabled** —
  every engine talks to MinIO with the same obvious dev credentials. One
  mental model, deterministic failures. (In production you'd use Nessie's
  credential-vending/signing instead — and never commit credentials.)
- **`fs.s3.enabled`** — Trino renamed `fs.native-s3.enabled` in 481; we use
  the new name.
- **MinIO pinned to Sept 2025** — MinIO archived its community repo in April
  2026, so this tag is frozen-forever-stable; its console keeps the object
  browser, which is all we need.
- **`mcp` pinned `< 2`** — MCP SDK v2 (breaking changes) goes beta end of
  June 2026.
- **In-memory Nessie, 4 containers, no Spark/Postgres/Airflow** — reliability
  and speed-to-running beat feature breadth in a 2-hour room.

### What was verified end-to-end (and what wasn't)

Verified by actually running it (macOS Apple Silicon, Docker 29 / Compose v5,
Python 3.13 — 2026-06-11): cold start from `docker compose down -v` to
all-healthy in ~18 s · `make seed` loads 48 + 360 rows · joins, `$snapshots`/
`$files` metadata tables, time travel via `"lots#<hash>"` and
`"lots#<timestamp>"`, `ALTER TABLE ADD COLUMN`, `UPDATE` · the Exercise 5
branch flow (curl + second catalog + diverging counts) · MCP stdio smoke test:
solution passes 3/3, the stub lists 3 tools and fails its TODOs as designed ·
seed idempotency (re-run resets to 360 rows).

**Not executed here:** clicking through the Claude Desktop GUI itself and
`mcp install` (documented from the official MCP docs). `make smoke` exercises
the identical stdio protocol path Claude Desktop uses, so if smoke passes,
only the config file can be wrong. Also untested: Windows hosts (commands are
documented but were verified on macOS/Linux-style shells only).

---

## 🇪🇸 Español

### Requisitos

- **Docker Desktop** (o Docker Engine con Compose **v2** — el comando
  `docker compose`, con espacio)
- **8 GB de RAM** mínimo y **10 GB de disco libre**
- **Python 3.11+** (3.10–3.13 funcionan)
- **Claude Desktop** (la cuenta gratuita sirve) para la parte del agente de IA —
  macOS o Windows. No existe versión para Linux; en Linux puedes hacer todo el
  taller igual y verificar el servidor MCP con `make smoke`.
- SQL básico y la terminal. `make` es cómodo pero opcional (cada comando crudo
  está en la [tabla sin make](#sin-make-no-hay-problema)).

### ⚠️ Antes del taller — haz esto en casa, con buen WiFi

El WiFi del evento no va a descargar **≈1.5 GB** de imágenes (≈3.8 GB en
disco) para todo el mundo a la vez. Por favor descarga antes:

```bash
git clone <este-repo> && cd your-own-lakehouse
docker compose pull          # ≈1.5 GB — vete por un café
```

Opcional pero recomendado (ahorra 2 minutos en el taller):

```bash
make venv                    # o: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Inicio rápido — el camino feliz

```bash
make up        # = docker compose up -d --wait     (arranque en frío ≈ 20–60 s)
make health    # chequeo de estado en una línea — espera tres OK
make seed      # crea y carga las tablas Iceberg (48 fincas, 360 lotes de café)
make trino     # abre una consola SQL. Prueba:
```

```sql
SELECT f.region, round(avg(l.cupping_score), 2) AS puntaje
FROM iceberg.coffee.lots l JOIN iceberg.coffee.farms f USING (farm_id)
GROUP BY f.region ORDER BY puntaje DESC;
```

Si eso devuelve las regiones cafeteras de Colombia ordenadas por calidad —
**tu lakehouse está vivo.** Sigue con
[exercises/EXERCISES.md](exercises/EXERCISES.md).

#### Tus tres servicios

| Servicio             | URL                      | Credenciales                 |
| -------------------- | ------------------------ | ---------------------------- |
| Consola de MinIO     | <http://localhost:9001>  | `minioadmin` / `minioadmin`  |
| UI de Nessie         | <http://localhost:19120> | ninguna                      |
| UI de Trino          | <http://localhost:8080>  | cualquier usuario, sin clave |

> ♻️ El catálogo corre **en memoria** a propósito (un contenedor menos):
> reiniciar el stack lo vacía. `make seed` lo reconstruye en segundos — y es
> también tu "botón de reinicio" después de experimentar. (`make down` detiene
> el stack; `make clean` borra además los datos de MinIO.)

### Conecta Claude Desktop (la parte del agente de IA)

El servidor MCP vive en [`mcp_server/`](mcp_server/): `server_solution.py`
funciona tal cual; `server.py` es la versión que **tú** completas en el
Ejercicio 4. Expone tres herramientas — `list_tables`, `describe_table`,
`run_sql` (solo lectura, máximo 200 filas) — y habla con Trino en
`localhost:8080`.

**Paso 0 — comprueba el servidor, sin Claude:**

```bash
make smoke     # = .venv/bin/python mcp_server/smoke_test.py
```

**Opción A — configuración manual (recomendada, siempre funciona).**
Abre el archivo de configuración (Claude Desktop → Settings → Developer →
Edit Config):

| SO      | Archivo de configuración                                          |
| ------- | ----------------------------------------------------------------- |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                     |

Pega esto (reemplaza `/RUTA/ABS/A` por tu ruta absoluta real — córrele `pwd`
dentro del repo; `~` no funciona aquí):

```json
{
  "mcpServers": {
    "lakehouse": {
      "command": "/RUTA/ABS/A/your-own-lakehouse/.venv/bin/python",
      "args": ["/RUTA/ABS/A/your-own-lakehouse/mcp_server/server_solution.py"]
    }
  }
}
```

En Windows usa doble backslash y la carpeta Scripts:

```json
{
  "mcpServers": {
    "lakehouse": {
      "command": "C:\\RUTA\\ABS\\A\\your-own-lakehouse\\.venv\\Scripts\\python.exe",
      "args": ["C:\\RUTA\\ABS\\A\\your-own-lakehouse\\mcp_server\\server_solution.py"]
    }
  }
}
```

Después **cierra Claude Desktop por completo** (en Windows: ciérralo desde la
bandeja del sistema, no solo la ventana) y vuelve a abrirlo. Las herramientas
`lakehouse` aparecen en el menú de herramientas del chat. Pregúntale:
*"¿Qué tablas hay en mi lakehouse y cuál región cafetera tiene mejor puntaje?"*

**Opción B — `mcp install` (si usas [uv](https://docs.astral.sh/uv/)).**
El CLI oficial de MCP escribe la entrada de configuración por ti — ojo: la
entrada generada lanza el servidor con `uv`, así que uv debe quedar instalado:

```bash
uv run mcp install mcp_server/server_solution.py --name lakehouse
```

### Flujo del taller

[exercises/EXERCISES.md](exercises/EXERCISES.md): tour por el stack → SQL
sobre Iceberg → metadatos, **viaje en el tiempo y evolución de esquema** →
completa el servidor MCP y conecta Claude → (extra) **ramifica tus datos como
en Git** con Nessie.

### Solución de problemas

| Síntoma | Solución |
| ------- | -------- |
| **Un puerto ya está en uso** (el 8080 es el clásico) | `cp .env.example .env`, cambia el/los puerto(s), `make up` de nuevo. `make seed`/`make health` leen `.env` automáticamente. Si cambiaste `TRINO_PORT`, agrega también `"env": {"TRINO_PORT": "<puerto>"}` a la entrada de Claude. |
| **`docker: command not found` / el daemon no corre** | Instala/inicia Docker Desktop. Se necesita Compose v2 (`docker compose version`). |
| **La descarga de imágenes es lenta o falla** (WiFi del evento…) | Corre `docker compose pull` en casa antes. Las descargas se reanudan si se interrumpen; verifica tener 10 GB libres. |
| **Errores estilo S3**: `NoSuchBucket`, `SignatureDoesNotMatch`, conexión rechazada en 9000 | El bucket `warehouse` se crea solo — revisa `docker compose logs minio-init`. MinIO necesita acceso path-style y endpoints explícitos; ambos ya vienen configurados en todo. Si cambiaste credenciales en `.env`, replícalas en `trino/catalog/iceberg.properties`. |
| **`Table 'iceberg.coffee.lots' does not exist`** después de un reinicio | Esperado: el catálogo es en memoria. Corre `make seed`. |
| **Claude Desktop no muestra las herramientas** | Las rutas del JSON deben ser **absolutas** (sin `~`); Windows necesita `\\` y `.venv\Scripts\python.exe`. Cierra Claude por completo (¡icono de bandeja!) y reábrelo. Logs: macOS `~/Library/Logs/Claude/mcp*.log`, Windows `%APPDATA%\Claude\logs`. El stack debe estar arriba — Claude lanza el servidor, pero quien responde es Trino. |
| **Las herramientas de Claude devuelven error** | `make health`, luego `make smoke`. Si smoke pasa, el problema es la configuración de Claude, no el servidor. |
| **La primera consulta tarda segundos** | Calentamiento de la JVM. La segunda es rápida. |
| **¿Apple Silicon?** | Todas las imágenes son multi-arch (arm64 + amd64). No hay que hacer nada. |

#### ¿Sin make? No hay problema

| Target de `make` | Comando crudo |
| ---------------- | ------------- |
| `make up`     | `docker compose up -d --wait` |
| `make health` | `docker compose ps` |
| `make venv`   | `python3 -m venv .venv` y luego `.venv/bin/pip install -r requirements.txt` (Windows: `.venv\Scripts\pip install -r requirements.txt`) |
| `make seed`   | `.venv/bin/python seed/seed_data.py` (Windows: `.venv\Scripts\python seed\seed_data.py`) |
| `make trino`  | `docker exec -it trino trino` |
| `make smoke`  | `.venv/bin/python mcp_server/smoke_test.py` |
| `make down`   | `docker compose down` |
| `make clean`  | `docker compose down -v` |

### Versiones fijadas (verificadas el 2026-06-11)

| Componente | Versión |
| ---------- | ------- |
| MinIO | `minio/minio:RELEASE.2025-09-07T16-13-09Z` (+ `mc RELEASE.2025-08-13T08-35-41Z`) |
| Nessie | `ghcr.io/projectnessie/nessie:0.107.9` |
| Trino | `trinodb/trino:481` |
| PyIceberg | `0.11.1` (+ pyarrow 24.0.0, s3fs 2026.4.0) |
| SDK de MCP | `mcp[cli] 1.27.2` |
| Cliente Python de Trino | `0.337.0` |

### Notas de diseño (por qué está construido así)

- **Catálogo Iceberg REST, no el conector nativo de Nessie en Trino** — REST
  es el protocolo estándar y neutral: el mismo endpoint sirve a Trino *y* a
  PyIceberg.
- **Peculiaridad de Nessie que vale la pena saber:** sirve exactamente **un
  snapshot de Iceberg por commit** (así garantiza consistencia entre tablas),
  por lo que el clásico `FOR VERSION AS OF` no aplica — viajas en el tiempo a
  través de los commits de Nessie:
  `SELECT … FROM "lots#<hash-del-commit-o-timestamp-UTC>"`. El Ejercicio 3
  enseña exactamente esto.
- **`pyiceberg[s3fs]`** — las respuestas REST de Nessie le indican a PyIceberg
  usar su FileIO de fsspec (`py-io-impl`), que depende de s3fs. Sin él, el
  seed falla con `ModuleNotFoundError: s3fs`.
- **Credenciales estáticas de MinIO en todas partes; firma de peticiones de
  Nessie desactivada** — cada motor habla con MinIO con las mismas credenciales
  obvias de desarrollo. Un solo modelo mental, fallos deterministas. (En
  producción usarías el vending/firmado de credenciales de Nessie — y jamás
  credenciales en archivos.)
- **`fs.s3.enabled`** — Trino renombró `fs.native-s3.enabled` en la 481;
  usamos el nombre nuevo.
- **MinIO fijado a sept. 2025** — MinIO archivó su repo comunitario en abril
  de 2026, así que ese tag es estable para siempre; su consola conserva el
  navegador de objetos, que es todo lo que necesitamos.
- **`mcp` fijado `< 2`** — el SDK v2 de MCP (con cambios incompatibles) entra
  en beta a fin de junio de 2026.
- **Nessie en memoria, 4 contenedores, sin Spark/Postgres/Airflow** — en un
  taller de 2 horas, la confiabilidad y la velocidad de arranque valen más que
  la amplitud de funciones.

### Qué se verificó de punta a punta (y qué no)

Verificado ejecutándolo de verdad (macOS Apple Silicon, Docker 29 / Compose
v5, Python 3.13 — 2026-06-11): arranque en frío desde `docker compose down -v`
hasta todo-saludable en ~18 s · `make seed` carga 48 + 360 filas · joins,
tablas de metadatos `$snapshots`/`$files`, viaje en el tiempo con
`"lots#<hash>"` y `"lots#<timestamp>"`, `ALTER TABLE ADD COLUMN`, `UPDATE` ·
el flujo de ramas del Ejercicio 5 (curl + segundo catálogo + conteos que
divergen) · smoke test MCP por stdio: la solución pasa 3/3, el stub lista las
3 herramientas y falla sus TODOs como está diseñado · idempotencia del seed
(re-ejecutarlo vuelve a 360 filas).

**No ejecutado aquí:** el clic final dentro de la GUI de Claude Desktop y
`mcp install` (documentados a partir de la documentación oficial de MCP).
`make smoke` ejerce exactamente el mismo camino stdio que usa Claude Desktop:
si smoke pasa, lo único que puede estar mal es el archivo de configuración.
Tampoco probado: hosts Windows (los comandos están documentados, pero se
verificaron solo en shells tipo macOS/Linux).

---

*Built for PyCon Colombia. Coffee data is synthetic (generated with a fixed
seed) — any resemblance to your favorite finca is a happy accident.* ☕

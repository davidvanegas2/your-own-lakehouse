# Workshop helpers. Every target is a thin wrapper around a plain command —
# if you don't have `make` (e.g. on Windows), copy the commands from here.

# Pick up port/credential overrides from .env, mirroring docker compose.
-include .env
export

VENV   := .venv
PYTHON := $(VENV)/bin/python

.PHONY: help up down clean health venv seed trino mcp smoke logs

help:
	@echo "make up      - start MinIO + Nessie + Trino and wait until healthy"
	@echo "make health  - quick status check of all services"
	@echo "make seed    - create and load the Iceberg tables (PyIceberg)"
	@echo "make trino   - open an interactive Trino SQL shell"
	@echo "make mcp     - run the MCP server (solution version) over stdio"
	@echo "make smoke   - end-to-end MCP smoke test (lists tools, runs a query)"
	@echo "make logs    - tail logs from all containers"
	@echo "make down    - stop the stack (table data in MinIO survives)"
	@echo "make clean   - stop the stack AND delete all data"

up:
	docker compose up -d --wait
	@echo ""
	@echo "All services are healthy. Next step: make seed"

down:
	docker compose down

clean:
	docker compose down -v

health:
	docker compose ps
	@curl -sf "http://localhost:$${MINIO_PORT:-9000}/minio/health/live" > /dev/null \
		&& echo "minio  : OK" || echo "minio  : DOWN"
	@curl -sf "http://localhost:$${NESSIE_PORT:-19120}/api/v2/config" > /dev/null \
		&& echo "nessie : OK" || echo "nessie : DOWN"
	@curl -s "http://localhost:$${TRINO_PORT:-8080}/v1/info" | grep -q '"starting":false' \
		&& echo "trino  : OK" || echo "trino  : DOWN (or still starting)"

# Creates the virtualenv the first time (or when requirements.txt changes).
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@touch $(VENV)/bin/activate

venv: $(VENV)/bin/activate

seed: venv
	$(PYTHON) seed/seed_data.py

trino:
	docker exec -it trino trino

mcp: venv
	$(PYTHON) mcp_server/server_solution.py

smoke: venv
	$(PYTHON) mcp_server/smoke_test.py

logs:
	docker compose logs -f

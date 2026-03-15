# Local Podman + Postgres

This stack is for local learning-scan runs only. Runtime DB data stays outside git-tracked content.

## 1) Prepare env file

```bash
cp .env.podman.example .env.podman
```

Update `.env.podman` values as needed.

## 2) Start local stack

```bash
podman compose -f podman-compose.yml --env-file .env.podman up -d
```

Services:
- `postgres`: PostgreSQL 16 with host bind mount at `./.local/postgres-data`
- `learning-base`: base Python/Linux worker container with repository mounted at `/workspace`

Current volume mappings:
- Postgres data: host `./.local/postgres-data` -> container `/var/lib/postgresql/data`
- Postgres init SQL: host `./infra/postgres/init` -> container `/docker-entrypoint-initdb.d` (read-only)
- Workspace in learning container: host `./` -> container `/workspace`

## 2.1) Apply or refresh schema on an existing DB

Init SQL under `infra/postgres/init/` runs automatically only for a fresh Postgres data directory.
If your database already exists, apply schema changes manually:

```bash
podman exec -i ard-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < infra/postgres/init/001_extensions.sql

podman exec -i ard-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < infra/postgres/init/010_learning_schema.sql
```

Quick verify:

```bash
podman exec -it ard-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "\dt learning.*"
```

## 3) Verify DB health

```bash
podman ps --format '{{.Names}}\t{{.Status}}'
podman exec -it ard-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 3.1) Run learning-loop persistence smoke test

This runs one successful local role scan and one intentional failure target,
then persists both records and prints recent batch summaries.

```bash
set -a; . ./.env.podman; set +a
.venv/bin/python scripts/learning_batch_smoke.py --run-label local-smoke
```

Optional custom targets:

```bash
.venv/bin/python scripts/learning_batch_smoke.py \
  --role-path src/ansible_role_doc/tests/roles/base_mock_role \
  --role-path missing-role-does-not-exist \
  --run-label custom-smoke
```

Use a guaranteed-missing path for the failure target. If a directory exists (even
an empty one), the scan may be counted as a success and hide failure-path metrics.

## 3.2) Run a repo URL batch (Postgres-first)

You can provide repository URLs either by repeating `--repo-url` or by passing
`--repo-url-file` (one URL per line; blank lines and `#` comments are ignored).

```bash
set -a; . ./.env.podman; set +a
.venv/bin/python scripts/learning_repo_batch.py \
  --repo-url https://github.com/geerlingguy/ansible-role-nginx \
  --repo-url https://github.com/geerlingguy/ansible-role-apache \
  --run-label repo-smoke
```

URL file example:

```bash
set -a; . ./.env.podman; set +a
.venv/bin/python scripts/learning_repo_batch.py \
  --repo-url-file scripts/repo_urls.example.txt \
  --repo-style-readme-path README.md \
  --repo-role-path . \
  --run-label repo-file-smoke
```

Freshness control options:

```bash
# default behavior: skip targets scanned in the last 7 days
.venv/bin/python scripts/learning_repo_batch.py \
  --repo-url-file scripts/repo_urls.example.txt \
  --run-label repo-fresh-default

# disable freshness skipping for a full rescan
.venv/bin/python scripts/learning_repo_batch.py \
  --repo-url-file scripts/repo_urls.example.txt \
  --force-rescan \
  --run-label repo-full-rescan
```

Recent reference run:

- Sample wide run `sample12-20260315-193723` completed with `12/12` successful repo scans and `0` failures.

No additional folder mapping is required for repo URLs themselves. Only the URL
list file must exist in the mapped workspace path (for local runs this repo
root is already available).

## 4) Create a checkpoint with `pg_dump`

Create a logical backup file in an ignored local folder:

```bash
mkdir -p .local/db-checkpoints
podman exec -i ard-postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --format=custom \
  > ".local/db-checkpoints/scan_$(date +%Y%m%d_%H%M%S).dump"
```

## 5) Restore from a checkpoint

```bash
podman exec -i ard-postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  < .local/db-checkpoints/<checkpoint-file>.dump
```

## 6) Stop stack

```bash
podman compose -f podman-compose.yml --env-file .env.podman down
```

To remove local DB data too:

```bash
rm -rf .local/postgres-data
```

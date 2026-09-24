# Data Lakehouse Implementation

Created time: 28 April 2026 13:46
Month: 4. APRIL

## Start the local stack

Run these commands from this repository's directory:

1. Start Docker Desktop and wait until Docker is ready.
2. If Airbyte has never been installed on this machine, run `make airbyte-install` once.
3. On each subsequent startup, run `make up`.

`make up` starts SeaweedFS, Nessie, and Trino with Docker Compose, then resumes the existing Airbyte installation. **Do not run `docker compose up` first**; `make up` already does that. To run only the three Compose services, use `docker compose up -d` instead. To check their status, run `docker compose ps`; Airbyte is normally available at `http://localhost:8000`.

# Concept 💡

[What Is a Data Lakehouse? | IBM](https://www.ibm.com/think/topics/data-lakehouse#179371084)

# Lakehouse tools

[https://github.com/manuzhang/awesome-lakehouse](https://github.com/manuzhang/awesome-lakehouse)

# Structure

The architecture of a data lakehouse typically consists of five layers:

- **Ingestion layer**
- **Storage layer**
- **Metadata layer**
- **API layer**
- **Consumption layer**

# I. Ingestion layer

This first layer collects data from a range of internal and external sources and prepares it for storage and analysis. The [ingestion](https://www.ibm.com/think/topics/data-ingestion) layer can use connectors to integrate with sources such as [database management systems](https://www.ibm.com/docs/en/zos-basic-skills?topic=zos-what-is-database-management-system), [NoSQL databases](https://www.ibm.com/think/topics/nosql-databases), [SaaS](https://www.ibm.com/think/topics/saas) applications and social media feeds. Ingestion can be either [batch](https://www.ibm.com/think/topics/batch-jobs) or in real time.

[https://github.com/airbytehq/airbyte](https://github.com/airbytehq/airbyte)

1. **Install `abctl`**

```bash
curl -LsfS https://get.airbyte.com | bash -
```

1. **Install Airbyte (first-time setup only)**

```bash
# normal (run from this repository)
make airbyte-install

# or in low-resource mode
make airbyte-install AIRBYTE_INSTALL_ARGS="--no-browser --low-resource-mode"
```

To run Airbyte in a low-resource environment (fewer than 4 CPUs), specify the **`--low-resource-mode`** flag to the local install command. In low-resource mode, you are **unable** to access the Connector Builder.

1. **Set up authentication**

```bash
abctl local credentials

# results
Credentials:
Email: user@example.com
Password: a-random-password
Client-Id: 03ef466c-5558-4ca5-856b-4960ba7c161b # <- store this
Client-Secret: m2UjnDO4iyBQ3IsRiy5GG3LaZWP6xs9I # <- store this
```

- Return to your browser and use that password to log into Airbyte.
- Optional: Since you probably want to set your own password, you can change it any time.

    ```bash
    abctl local credentials --password <YourStrongPasswordExample>
    ```


# II. Storage layer and local stack

[SeaweedFS](https://github.com/seaweedfs/seaweedfs) provides S3-compatible object storage. The local stack runs through [docker-compose.yml](docker-compose.yml):

```text
Airbyte → SeaweedFS (ingested files)
Trino → Nessie (Iceberg catalog)
Trino → SeaweedFS (Iceberg data and metadata files)
DBeaver / Superset → Trino (SQL)
```

`make up` starts SeaweedFS, Nessie, and Trino through Compose and resumes the existing Airbyte Kind containers. Superset still runs separately.

Airbyte uses Kubernetes inside Docker, managed by `abctl`; its [Docker Compose deployment is deprecated](https://github.com/airbytehq/airbyte/discussions/40599). Routine startup does not reinstall or upgrade Airbyte. Use `make airbyte-install` only for initial setup or an intentional upgrade: [`abctl local install`](https://github.com/airbytehq/abctl#install) updates existing installations and defaults to the latest chart. To select a chart version, pass `AIRBYTE_INSTALL_ARGS="--no-browser --chart-version <version>"` and retain any custom `--values` settings.

## 1. Configure and start the stack

Prerequisites: running Docker with Docker Compose (supporting `up --wait`), Make, Bash, `abctl`, an existing Airbyte installation, plus the AWS CLI for the bucket setup below. Run these commands from the repository root.

```bash
# First-time setup; keep an existing .env if already configured.
cp .env.example .env
```

Set `S3_ACCESS_KEY` and `S3_SECRET_KEY` in `.env`. Compose passes these values to Trino. The current SeaweedFS service has no S3 authentication configuration mounted, so setting these variables alone does not configure server-side access control.

```bash
make up
```

The command checks prerequisites and the existing Airbyte cluster before starting services. It waits up to 180 seconds for Compose services to become healthy, starts stopped Airbyte nodes, and prints `abctl local status`. Already-running Airbyte nodes are left running; Kubernetes workloads may need additional time before the UI is ready (default: `http://localhost:8000`).

The default Kind cluster label is `airbyte-abctl`. For a custom cluster, use `AIRBYTE_CLUSTER_NAME=<name> make up`. If no matching container exists, check your Docker context or run the first-time installation above. Startup failures do not roll back services that already started; resolve the reported error and rerun `make up`.

To start only the lakehouse services, use `docker compose up -d`.

SeaweedFS runs `server -s3 -dir=/data` and persists its data in `./docker/warehouse/data`. Trino starts after the SeaweedFS and Nessie health checks pass.

| Service | Host endpoint | Endpoint inside the Compose network |
| --- | --- | --- |
| SeaweedFS S3 API | `http://localhost:8333` | `http://seaweedfs:8333` |
| SeaweedFS master | `http://localhost:9333` | `http://seaweedfs:9333` |
| SeaweedFS filer | `http://localhost:8888` | `http://seaweedfs:8888` |
| Nessie API | `http://localhost:19120/api/v2` | `http://nessie:19120/api/v2` |
| Trino | `http://localhost:8080` | `http://trino:8080` |

## 2. Create the warehouse bucket

Trino uses `s3://catalog/` as its fallback warehouse. This bucket is for tables created directly through Trino and is not used by Airbyte destinations. Compose does not create the bucket automatically. Once SeaweedFS is ready, create it using the AWS CLI:

```bash
set -a
. ./.env
set +a
export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
export AWS_DEFAULT_REGION=us-east-1

aws --endpoint-url http://localhost:8333 s3 mb s3://catalog
aws --endpoint-url http://localhost:8333 s3 ls
```

Skip `s3 mb` if the bucket already exists.

## 3. Inspect or stop the stack

```bash
docker compose ps
abctl local status
docker compose logs --tail=100 seaweedfs nessie trino

# Stop the lakehouse services and Airbyte containers; restart with make start.
make stop
```

`make stop` keeps the Compose containers and SeaweedFS files in `docker/warehouse/data` for `make start`. Nessie has no persistent backend configured in this Compose file, so recreating its container loses catalog state even if the object files remain.

# III. Ingestion → Storage

Create one Airbyte **S3 Data Lake** destination for each source database. Use the normalized database name as both the SeaweedFS bucket and Nessie namespace:

| Setting | Value |
| --- | --- |
| S3 endpoint | `http://host.docker.internal:8333` |
| S3 bucket name | `<dbname>` |
| Warehouse location | `s3://<dbname>` |
| S3 bucket region | `us-east-1` |
| AWS access key ID | The `S3_ACCESS_KEY` value in `.env` |
| AWS secret access key | The `S3_SECRET_KEY` value in `.env` |
| Catalog type | `Nessie` |
| Nessie server URI | `http://host.docker.internal:19120/api/v2` |
| Default namespace (Nessie) | `<dbname>` |
| Main branch name | `main` |
| Normalize column names | Enabled |

Airbyte installed with `abctl` runs in a Kind cluster outside the Compose network. From connector workloads, `localhost` points to the workload itself and the Compose service names are not automatically resolvable. On Docker Desktop, use `host.docker.internal` to reach SeaweedFS and Nessie on the host.

Before creating the destination, create its bucket:

```bash
aws --endpoint-url http://localhost:8333 s3 mb s3://<dbname>
```

Use lowercase letters and numbers for `<dbname>`, starting with a letter. This keeps the same name valid for both S3 and Nessie. Examples:

| Source database | Bucket | Warehouse | SeaweedFS logical root |
| --- | --- | --- | --- |
| `dummyjson` | `dummyjson` | `s3://dummyjson` | `/buckets/dummyjson` |
| `customer` | `customer` | `s3://customer` | `/buckets/customer` |
| `invoice` | `invoice` | `s3://invoice` | `/buckets/invoice` |

Each Airbyte connection must use the destination created for its source database. The connection name does not determine the bucket. Iceberg creates and manages table-specific data and metadata paths inside the bucket. See [AIRBYTE.md](AIRBYTE.md) for the concise rules.

S3 Data Lake writes Iceberg tables and registers them in Nessie, so Trino can query them through the `lakehouse` catalog after a successful sync.

# IV. Metadata layer

[Project Nessie](https://projectnessie.org/) tracks the Iceberg catalog. Compose starts the `nessie` service and exposes port `19120`; no separate `docker run` is needed.

Trino connects to `http://nessie:19120/api/v2` and uses the `main` reference. Nessie tracks catalog entries; Iceberg data and metadata files live in SeaweedFS.

# API layer

Trino exposes the Iceberg catalog as `lakehouse`. Compose mounts [docker/trino/catalog/lakehouse.properties](docker/trino/catalog/lakehouse.properties) into `/etc/trino/catalog/lakehouse.properties`:

```properties
connector.name=iceberg

iceberg.catalog.type=nessie
iceberg.nessie-catalog.uri=http://nessie:19120/api/v2
iceberg.nessie-catalog.ref=main
iceberg.nessie-catalog.default-warehouse-dir=s3://catalog/

fs.s3.enabled=true
s3.region=us-east-1
s3.endpoint=http://seaweedfs:8333
s3.aws-access-key=${ENV:S3_ACCESS_KEY}
s3.aws-secret-key=${ENV:S3_SECRET_KEY}
s3.path-style-access=true
```

After editing the catalog file, restart Trino:

```bash
docker compose restart trino
```

After changing credentials in `.env`, recreate Trino to load the new environment:

```bash
docker compose up -d --force-recreate trino
```

## Verify the flow

Check the catalog, then open the Trino CLI:

```bash
docker compose exec trino trino --execute "SHOW CATALOGS"
docker compose exec trino trino --catalog lakehouse
```

Run this SQL to exercise catalog creation, object writes, and reads:

```sql
CREATE SCHEMA IF NOT EXISTS lakehouse.demo;
CREATE TABLE lakehouse.demo.storage_check (id INTEGER, message VARCHAR);
INSERT INTO lakehouse.demo.storage_check VALUES (1, 'Hello SeaweedFS');
SELECT * FROM lakehouse.demo.storage_check;
DROP TABLE lakehouse.demo.storage_check;
```

In DBeaver, choose the Trino driver and connect to host `localhost`, port `8080`, catalog `lakehouse`, and user `tester`. Use schema `demo` after running the example above. The current stack does not configure Trino authentication.

# V. Consumption layer

[Quickstart | Superset](https://superset.apache.org/user-docs/quickstart)

Superset is part of this repository's Compose stack and is available at
`http://localhost:8088`. Its custom image installs the Trino Python driver from
[`docker/superset/Dockerfile`](docker/superset/Dockerfile).

After changing the Superset Dockerfile, rebuild and recreate its services:

```bash
docker compose up -d --build --force-recreate superset-init superset
```

Log in with username `admin` and the `SUPERSET_ADMIN_PASSWORD` value from
`.env`.

## Connect Superset to Trino

In Superset, open **Settings → Data: Database Connections → + Database** and
create a connection named `Lakehouse` with this SQLAlchemy URI:

```text
trino://tester@trino:8080/lakehouse/default
```

Use the Compose service name `trino`, not `localhost`, because Superset connects
from its container. The current Trino service has no authentication, so the
username identifies the query user and no password is required.

Select **Test Connection**, then **Connect**. To use the Airbyte data, open
**Data → Datasets → + Dataset** and select:

- Database: `Lakehouse`
- Schema: `default`
- Table: `users`

Verify it in SQL Lab:

```sql
SELECT count(*) FROM lakehouse.default.users;
```

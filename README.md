# Data Lakehouse Implementation

Created time: 28 April 2026 13:46
Month: 4. APRIL

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

1. **Start `airbyte`** 

```bash
# normal
abctl local install

# or in low-resource mode
abctl local install --low-resource-mode
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

Airbyte and Superset run separately; Compose starts SeaweedFS, Nessie, and Trino.

## 1. Configure and start the stack

Prerequisites: Docker with Docker Compose, plus the AWS CLI for the bucket setup below. Run these commands from the repository root.

```bash
# First-time setup; keep an existing .env if already configured.
cp .env.example .env
```

Set `S3_ACCESS_KEY` and `S3_SECRET_KEY` in `.env`. Compose passes these values to Trino. The current SeaweedFS service has no S3 authentication configuration mounted, so setting these variables alone does not configure server-side access control.

```bash
mkdir -p docker/warehouse/data
docker compose up -d
docker compose ps
```

SeaweedFS runs `server -s3 -dir=/data` and persists its data in `./docker/warehouse/data`. Trino starts after the SeaweedFS and Nessie health checks pass.

| Service | Host endpoint | Endpoint inside the Compose network |
| --- | --- | --- |
| SeaweedFS S3 API | `http://localhost:8333` | `http://seaweedfs:8333` |
| SeaweedFS master | `http://localhost:9333` | `http://seaweedfs:9333` |
| SeaweedFS filer | `http://localhost:8888` | `http://seaweedfs:8888` |
| Nessie API | `http://localhost:19120/api/v2` | `http://nessie:19120/api/v2` |
| Trino | `http://localhost:8080` | `http://trino:8080` |

## 2. Create the warehouse bucket

Trino uses `s3://catalog/` as its warehouse. Compose does not create the bucket automatically. Once SeaweedFS is ready, create it using the AWS CLI:

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
docker compose logs --tail=100 seaweedfs nessie trino
docker compose down
```

Stopping the stack preserves the SeaweedFS bind-mounted files in `docker/warehouse/data`; `docker compose down -v` does not remove those files either. Nessie has no persistent backend configured in this Compose file, so catalog state is not preserved when its container is recreated, even if the object files remain.

# III. Ingestion → Storage

Configure Airbyte's S3 destination to use SeaweedFS:

| Setting | Value |
| --- | --- |
| S3 endpoint | `http://<reachable-host>:8333` |
| Bucket | `catalog` |
| Bucket path / prefix | `raw/` (keep ingested files separate from Iceberg tables) |
| Region | `us-east-1` |
| Access key ID | The `S3_ACCESS_KEY` value in `.env` |
| Secret access key | The `S3_SECRET_KEY` value in `.env` |
| Path-style access | Enable if exposed by the connector |

Use an address reachable from the Airbyte connector runtime. Airbyte installed with `abctl` runs separately from the Compose network: `localhost` points to the connector itself, and the Compose service name `seaweedfs` is not automatically resolvable there. Use the Docker host's reachable IP or a host gateway name supported by your environment.

Writing files through an S3 destination does not automatically register Iceberg tables in Nessie. An Iceberg-aware ingestion or transformation step must create the tables before Trino can query them through the `lakehouse` catalog.

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

**1. Get Superset**

```bash
git clone https://github.com/apache/superset
```

**2. Start the latest official release of Superset**

```bash
# Enter the repository you just cloned
$ cd superset

# Set the repo to the state associated with the latest official version
$ git checkout tags/6.0.0

# Fire up Superset using Docker Compose
$ docker compose -f docker-compose-image-tag.yml up
```

This may take a moment as Docker Compose will fetch the underlying container images and will load up some examples. Once all containers are downloaded and the output settles, you're ready to log in.

⚠️ If you get an error message like `validating superset\docker-compose-image-tag.yml: services.superset-worker-beat.env_file.0 must be a string`, you need to update your version of `docker-compose`. Note that `docker-compose` is on the path to deprecation and you should now use `docker compose` instead.

#### **3. Log into Superset**

Now head over to [http://localhost:8088](http://localhost:8088/) and log in with the default created account:

```bash
username: admin
password: admin
```

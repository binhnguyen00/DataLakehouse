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
    

# II. **Storage layer**

**Minio**

[https://github.com/minio/minio](https://github.com/minio/minio)

**Minio** alternative

[https://github.com/seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)

<aside>
💡

**MinIO Note**

THIS REPOSITORY IS NO LONGER MAINTAINED.

**Alternatives:**

- [**AIStor Free**](https://min.io/download) — Full-featured, standalone edition for community use (free license)
- [**AIStor Enterprise**](https://min.io/pricing) — Distributed edition with commercial support
</aside>

1. **Docker pull minio**

```bash
docker pull quay.io/minio/aistor/minio
```

1. **Create the directory structure**

Create directories for data and certificates. The following example uses **`$HOME/minio`** as the base path.

```bash
mkdir -p $HOME/minio/data $HOME/minio/certs
```

1. **Retrieve your license file**

MinIO AIStor requires a license to run

Download the license file to **`$HOME/minio/minio.license`** for use in later steps.

![29-04-29@03.47.07.png](Data%20Lakehouse%20Implementation/29-04-2903.47.07.png)

- **`$HOME/minio/data`** to **`/mnt/data`** for object storage
- **`$HOME/minio/minio.license`** to **`/minio.license`** for the license file
- **`$HOME/minio/certs`** to **`/etc/minio/certs`** for TLS certificates (if configured)
1. **Run AIStor Server**

```bash
docker run -dt                                             \
  -p 9000:9000 -p 9001:9001                                \
  -v $HOME/minio/data:/mnt/data                            \
  -v $HOME/minio/minio.license:/minio.license              \
  -v $HOME/minio/certs:/etc/minio/certs                    \
  --name "mobifone-aistor-server"                          \
  quay.io/minio/aistor/minio:latest minio server /mnt/data \
  --license /minio.license
```

```bash
docker logs mobifone-aistor-server
```

The output of the `logs` command includes the startup message from the AIStor Server. To access the server, use the `localhost` or `127.0.0.1` address on your local host machine.

1. **Install AIStor client**

```bash
# ARM
curl --progress-bar -L https://dl.min.io/aistor/mc/release/linux-arm64/mc -o mc
chmod +x ./mc
sudo mv ./mc /usr/local/bin

# AMD
curl --progress-bar -L https://dl.min.io/aistor/mc/release/linux-amd64/mc -o mc
chmod +x ./mc
sudo mv ./mc /usr/local/bin/

mc --version
```

1. **Connect to the deployment**

Open your browser to [**http://localhost:9001**](http://localhost:9001/).

Log in using the default **minioadmin/ minioadmin** username and password.

# III. Ingestion → Storage

To push data from `source`  → `destination` , you need a access key generated from MinIO to allow Airbyte to connect.

*For example:*

| Access Key | ySa03lPsEWmzI0tseeeg |
| --- | --- |
| Secret Key | yuu1Ps3gDjfBRCCcmuv0act22Jw5ulhF4RvL0r0Q |

# IV. Metadata layer

[Project Nessie: Transactional Catalog for Data Lakes with Git-like semantics](https://projectnessie.org/)

**Implementation via docker**

```bash
docker pull ghcr.io/projectnessie/nessie:0.107.5

docker run -p 19120:19120 -p 9000:9000 ghcr.io/projectnessie/nessie:0.107.5

# should change port to 9002:9000. MinIO is using port 9000.
```

**Results**

![04-05-04@02.23.44.png](Data%20Lakehouse%20Implementation/04-05-0402.23.44.png)

![04-05-04@02.23.32.png](Data%20Lakehouse%20Implementation/04-05-0402.23.32.png)

![04-05-04@02.23.20.png](Data%20Lakehouse%20Implementation/04-05-0402.23.20.png)

# API layer

[Trino in a Docker container — Trino 480 Documentation](https://trino.io/docs/current/installation/containers.html)

**Implementation via docker**

```bash
docker run --name trino -d -p 8080:8080 trinodb/trino
```

Create a **`minio.properties`** 

```prolog
connector.name=iceberg

iceberg.catalog.type=nessie
iceberg.nessie-catalog.uri=http://host.docker.internal:19120/api/v2
iceberg.nessie-catalog.ref=main
iceberg.nessie-catalog.default-warehouse-dir=s3://catalog/

fs.native-s3.enabled=true
s3.region=us-east-1
s3.endpoint=http://host.docker.internal:9000
s3.aws-access-key=minio-access-key
s3.aws-secret-key=minio-secret-key
s3.path-style-access=true
```

Copy **`minio.properties`** to docker env. This helps `trino` connect to your minio server

```bash
docker cp path/to/minio.properties trino:/etc/trino/catalog/minio.properties
```

Now you can start the container. After that:

1. Connect to trino using **`dbeaver`**

![04-05-04@06.59.10.png](Data%20Lakehouse%20Implementation/04-05-0406.59.10.png)

1. Connection success, you can query as usual

![04-05-04@07.00.06.png](Data%20Lakehouse%20Implementation/04-05-0407.00.06.png)

# V. Consumtion layer

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
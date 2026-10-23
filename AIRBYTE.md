# Airbyte storage rules

Each source database uses its own SeaweedFS bucket and its own Airbyte S3 Data
Lake destination. The bucket name is the normalized database name:

```text
/buckets/<dbname>
```

Use lowercase letters and numbers, starting with a letter. Keep names simple so
the same value can be used safely as both the S3 bucket and Nessie namespace.

Configure each destination as follows:

```text
S3 bucket name        : <dbname>
Warehouse location    : s3://<dbname>
Nessie namespace      : <dbname>
Nessie branch         : main
```

Examples:

```text
dummyjson -> /buckets/dummyjson
customer  -> /buckets/customer
invoice   -> /buckets/invoice
```

An Airbyte connection must use the destination created for its source database.
The connection name does not control the bucket. Iceberg manages table-specific
`data` and `metadata` paths inside each bucket; do not create or rename those
paths manually.

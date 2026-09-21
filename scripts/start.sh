#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

for dependency in docker abctl; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing $dependency. Install it before running make up." >&2
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable. Start Docker Desktop or the Docker daemon, then retry make up." >&2
  exit 1
fi
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and configure it first." >&2
  exit 1
fi

# Kind labels identify the cluster without relying on a generated container name.
cluster_name="${AIRBYTE_CLUSTER_NAME:-airbyte-abctl}"
node_ids="$(docker ps -aq --filter "label=io.x-k8s.kind.cluster=$cluster_name")"
if [[ -z "$node_ids" ]]; then
  echo "Airbyte cluster '$cluster_name' was not found in the current Docker context." >&2
  echo "For a new installation, run make airbyte-install, then retry make up." >&2
  exit 1
fi

mkdir -p docker/warehouse/data
docker compose up -d --wait --wait-timeout 180

while IFS= read -r node_id; do
  is_running="$(docker inspect --format '{{.State.Running}}' "$node_id")"
  if [[ "$is_running" != true ]]; then
    docker start "$node_id"
  fi
done <<< "$node_ids"

echo "Lakehouse services are healthy. Airbyte containers are running; its workloads may still be starting."
abctl local status

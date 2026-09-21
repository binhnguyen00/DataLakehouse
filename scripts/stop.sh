#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Missing docker. Install it before running make stop." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable. Start Docker Desktop or the Docker daemon, then retry make stop." >&2
  exit 1
fi
docker compose version >/dev/null

cluster_name="${AIRBYTE_CLUSTER_NAME:-airbyte-abctl}"
node_ids="$(docker ps -q --filter "label=io.x-k8s.kind.cluster=$cluster_name")"
if [[ -n "$node_ids" ]]; then
  while IFS= read -r node_id; do
    docker stop "$node_id"
  done <<< "$node_ids"
fi

docker compose stop
echo "Lakehouse services and Airbyte containers stopped."

#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-psych-phenotyping-dev}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "El contenedor $CONTAINER_NAME no está corriendo. Ejecuta primero: bash scripts/docker_up.sh"
  exit 1
fi

docker exec -it "$CONTAINER_NAME" bash

#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-psych-phenotyping-dev}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "El contenedor $CONTAINER_NAME no está corriendo. Ejecuta primero: bash scripts/docker_up.sh"
  exit 1
fi

echo "==> Running runtime check"
docker exec "$CONTAINER_NAME" python scripts/check_runtime.py

echo
echo "==> Running pipeline dry-run"
docker exec "$CONTAINER_NAME" python scripts/regenerar_pipeline_desarrollo.py --dry-run

echo
echo "==> Docker smoke test OK"

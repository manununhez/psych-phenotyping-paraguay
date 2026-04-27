#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-psych-phenotyping-dev}"

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "==> Stopping container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" >/dev/null || true
  echo "==> Removing container: $CONTAINER_NAME"
  docker rm "$CONTAINER_NAME" >/dev/null || true
else
  echo "==> Container not found: $CONTAINER_NAME"
fi

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-psych-phenotyping-paraguay}"
IMAGE_TAG="${IMAGE_TAG:-dev}"
CONTAINER_NAME="${CONTAINER_NAME:-psych-phenotyping-dev}"
CONTAINER_MODE="${CONTAINER_MODE:-dev}"
HF_CACHE_DIR="${HF_CACHE_DIR:-$REPO_ROOT/.docker_cache/huggingface}"
HOST_DATA_DIR="${HOST_DATA_DIR:-$REPO_ROOT/data}"

mkdir -p "$HF_CACHE_DIR"

ENV_ARGS=()
if [[ -f "$REPO_ROOT/.env.docker" ]]; then
  ENV_ARGS+=(--env-file "$REPO_ROOT/.env.docker")
fi

RUN_ARGS=(
  -d
  --name "$CONTAINER_NAME"
  -w /workspace
  -v "$HF_CACHE_DIR:/root/.cache/huggingface"
)

case "$CONTAINER_MODE" in
  dev)
    RUN_ARGS+=(-v "$REPO_ROOT:/workspace")
    ;;
  snapshot)
    if [[ -d "$HOST_DATA_DIR" ]]; then
      RUN_ARGS+=(-v "$HOST_DATA_DIR:/workspace/data")
    fi
    ;;
  *)
    echo "Modo inválido: $CONTAINER_MODE. Usa CONTAINER_MODE=dev o CONTAINER_MODE=snapshot."
    exit 1
    ;;
esac

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "==> Starting existing container: $CONTAINER_NAME"
  docker start "$CONTAINER_NAME" >/dev/null
else
  echo "==> Creating container: $CONTAINER_NAME (mode=$CONTAINER_MODE)"
  DOCKER_CMD=(docker run)
  DOCKER_CMD+=("${RUN_ARGS[@]}")
  if [[ ${#ENV_ARGS[@]} -gt 0 ]]; then
    DOCKER_CMD+=("${ENV_ARGS[@]}")
  fi
  DOCKER_CMD+=("${IMAGE_NAME}:${IMAGE_TAG}" tail -f /dev/null)
  "${DOCKER_CMD[@]}" >/dev/null
fi

docker ps --filter "name=^/${CONTAINER_NAME}$"
echo "==> Container ready. Open a shell with: bash scripts/docker_shell.sh"

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-psych-phenotyping-paraguay}"
IMAGE_TAG="${IMAGE_TAG:-dev}"

cd "$REPO_ROOT"

echo "==> Building ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
echo "==> Build completed"

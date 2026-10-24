#!/usr/bin/env bash
set -euo pipefail

NS=rabbit-hole
CONTEXT=kind-rabbit-hole
IMAGE=ghcr.io/srijan1683/the-rabbit-hole
TAG="${IMAGE_TAG:?Set IMAGE_TAG to a commit SHA that exists in GHCR}"
ENV_FILE="${ENV_FILE:-.env}"

k() { kubectl --context "$CONTEXT" -n "$NS" "$@"; }

# Secret and DB init SQL are created from local files, so nothing sensitive is committed
k create secret generic app-secrets --from-env-file="$ENV_FILE" --dry-run=client -o yaml | k apply -f -
k create configmap db-init --from-file=init.sql=migrations/001_initial_schema.sql --dry-run=client -o yaml | k apply -f -

k apply -f k8s/postgres.yaml
sed "s|__IMAGE__|${IMAGE}:${TAG}|" k8s/app.yaml | k apply -f -

k rollout status statefulset/db --timeout=180s
k rollout status deployment/app --timeout=300s
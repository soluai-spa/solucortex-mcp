#!/usr/bin/env bash
# Deploy solucortex-mcp to Cloud Run (SCX-MCP-09).
#
# Multi-tenant remote MCP: the service stores NO tenant credentials — every request
# carries its own API key, so no secrets are configured here. Invoker is public
# (allow-unauthenticated); real auth is the per-request Bearer key (401 without it).
#
# Usage: deploy/cloudrun.sh [tag]      (default tag: current git short SHA)
# Requires: gcloud authenticated with an account that can push to Artifact Registry
# and deploy Cloud Run in project "solucortex".
set -euo pipefail

PROJECT=solucortex
REGION=southamerica-west1
AR_REPO=solucortex                       # same Artifact Registry repo as the main app (prod)
SERVICE=solucortex-mcp
TAG="${1:-$(git -C "$(dirname "$0")/.." rev-parse --short HEAD)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${AR_REPO}/${SERVICE}:${TAG}"

echo ">> Build ${IMAGE}"
docker build -t "${IMAGE}" "$(dirname "$0")/.."

echo ">> Push"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker push "${IMAGE}"

echo ">> Deploy ${SERVICE} (${REGION})"
gcloud run deploy "${SERVICE}" \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --image "${IMAGE}" \
  --allow-unauthenticated \
  --set-env-vars MCP_TRANSPORT=http \
  --port 8080 \
  --min-instances 0 \
  --max-instances 3 \
  --memory 256Mi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 300

URL=$(gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" --format='value(status.url)')
echo ">> Smoke test ${URL}"
curl -fsS "${URL}/health" && echo " <- health OK"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${URL}/mcp" -d '{}')
[ "${code}" = "401" ] && echo "401 sin key OK" || { echo "ERROR: se esperaba 401 sin key, llegó ${code}"; exit 1; }
echo ">> Listo: ${URL}"

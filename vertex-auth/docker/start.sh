#!/usr/bin/env bash
set -euo pipefail

# Expects these envs to be set via Fly secrets:
#   FLY_OIDC_AUD
#   GOOGLE_WIF_AUDIENCE
#   GOOGLE_IMPERSONATED_SA
# Renders the external account JSON on boot (ephemeral)
if [ ! -f /app/config/gcp-workload-identity.json ]; then
  echo "Rendering external account JSON..."
  /bin/bash /app/scripts/render_external_account.sh
fi

echo "Starting app..."
# Replace with your real entrypoint (uvicorn, celery, etc.)
python /app/test/test_vertex.py

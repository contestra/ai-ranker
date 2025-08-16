#!/usr/bin/env bash
set -euo pipefail

# Reads template and writes final external account JSON for ADC consumption.
# Requires:
#   GOOGLE_WIF_AUDIENCE  - //iam.googleapis.com/projects/NNN/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
#   GOOGLE_IMPERSONATED_SA - vertex-runner@contestra-ai.iam.gserviceaccount.com
#   FLY_OIDC_AUD - e.g. https://oidc.fly.io/contestra

: "${GOOGLE_WIF_AUDIENCE:?Set GOOGLE_WIF_AUDIENCE}"
: "${GOOGLE_IMPERSONATED_SA:?Set GOOGLE_IMPERSONATED_SA}"
: "${FLY_OIDC_AUD:?Set FLY_OIDC_AUD}"

tmpl="config/gcp_external_account.template.json"
out="config/gcp-workload-identity.json"

mkdir -p config

sed -e "s#\${GOOGLE_WIF_AUDIENCE}#${GOOGLE_WIF_AUDIENCE}#g" \
    -e "s#\${GOOGLE_IMPERSONATED_SA}#${GOOGLE_IMPERSONATED_SA}#g" \
    -e "s#\${FLY_OIDC_AUD}#${FLY_OIDC_AUD}#g" \
    "${tmpl}" > "${out}"

echo "Wrote ${out}"

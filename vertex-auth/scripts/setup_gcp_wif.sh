#!/usr/bin/env bash
set -euo pipefail

# ---------- EDIT THESE ----------
PROJECT_ID="contestra-ai"
POOL_ID="flyio-pool"
PROVIDER_ID="flyio-oidc"
ORG_SLUG="lee-dryburgh"                    # e.g. "co"
SA_EMAIL="vertex-runner@contestra-ai.iam.gserviceaccount.com"
# Optional: further restrict to a single Fly app by setting SUBJECT_PREFIX="org:app:"
SUBJECT_PREFIX="${ORG_SLUG}:"                   # e.g. "contestra:" or "contestra:my-app:"
ALLOWED_AUDIENCE="https://oidc.fly.io/${ORG_SLUG}"
# --------------------------------

echo ">> Enabling required APIs..."
gcloud services enable \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  iam.googleapis.com \
  aiplatform.googleapis.com \
  --project "${PROJECT_ID}"

echo ">> Getting project number..."
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
echo "PROJECT_NUMBER=${PROJECT_NUMBER}"

echo ">> Creating Workload Identity Pool (if not exists)..."
gcloud iam workload-identity-pools describe "${POOL_ID}" \
  --project "${PROJECT_ID}" --location="global" >/dev/null 2>&1 || \
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project "${PROJECT_ID}" --location="global" \
  --display-name="Fly.io Pool"

echo ">> Creating OIDC Provider (if not exists)..."
set +e
gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project "${PROJECT_ID}" --location="global" \
  --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1
EXISTS=$?
set -e

if [ "${EXISTS}" -ne 0 ]; then
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project "${PROJECT_ID}" --location="global" \
    --workload-identity-pool="${POOL_ID}" \
    --issuer-uri="https://oidc.fly.io/${ORG_SLUG}" \
    --allowed-audiences="${ALLOWED_AUDIENCE}" \
    --attribute-mapping="google.subject=assertion.sub,attribute.org=assertion.org_name,attribute.app=assertion.app_name,attribute.machine=assertion.machine_name,attribute.aud=assertion.aud,attribute.iss=assertion.iss" \
    --attribute-condition="assertion.iss=='https://oidc.fly.io/${ORG_SLUG}'"
else
  echo "Provider exists; skipping creation."
fi

POOL_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}"
PROVIDER_RESOURCE="${POOL_RESOURCE}/providers/${PROVIDER_ID}"
WIF_AUDIENCE="//iam.googleapis.com/${PROVIDER_RESOURCE}"

echo ">> Granting SA impersonation to identities from this pool/audience..."
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project "${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_RESOURCE}/attribute.aud/${ALLOWED_AUDIENCE}"

cat <<EOF

-----------------------------------------------------------------
SUCCESS.

Use these values in your deployment:

GOOGLE_WIF_AUDIENCE=${WIF_AUDIENCE}
FLY_OIDC_AUD=${ALLOWED_AUDIENCE}

(You'll place GOOGLE_WIF_AUDIENCE in config/gcp_external_account.template.json
 and set FLY_OIDC_AUD as an env var/secret in Fly.)

You can further restrict impersonation by subject:
  principalSet://iam.googleapis.com/${POOL_RESOURCE}/subject/${SUBJECT_PREFIX}*

-----------------------------------------------------------------
EOF

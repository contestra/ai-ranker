# Contestra: Keyless GCP Auth on Fly.io (Workload Identity Federation)

This bundle gives you a **turnkey**, keyless setup for Google Cloud from Fly.io Machines using **Workload Identity Federation (WIF)**.
It also covers **local development** via Application Default Credentials (ADC) without any JSON key files.

---

## What you get

- One-time **gcloud** script to create a Workload Identity **Pool** and **OIDC Provider** for Fly.io, and to grant SA impersonation.
- A tiny executable (`app/bin/flyio_openid_token`) that gets an OIDC token from the **local Fly Machines API socket** (`/.fly/api`).
- An **external account JSON** template consumed by Google client libraries to exchange that token for short‑lived Google creds.
- A **Dockerfile** + **start.sh** that wire everything up without hardcoding secrets or service account keys.
- A **Gemini smoke test** (`test/test_vertex.py`).

> Assumptions
> - Project ID: `contestra-ai`
> - Region/location for Vertex: `global`
> - Service Account email: `vertex-runner@contestra-ai.iam.gserviceaccount.com`
> - Fly org slug: `YOUR_FLY_ORG_SLUG` (replace it)
> - Pool/Provider IDs: `flyio-pool` / `flyio-oidc` (change if you prefer)

---

## 0) Local dev (do once per developer)

```bash
gcloud config set project contestra-ai
gcloud auth application-default login
```

This writes **ADC** to your user profile. No key files, no env vars required. Client libraries pick this up automatically.

---

## 1) One-time GCP setup for WIF (run from your laptop)

Edit the variables at the top of `scripts/setup_gcp_wif.sh` and run:

```bash
bash scripts/setup_gcp_wif.sh
```

This creates:
- Workload Identity **Pool** + **OIDC Provider** with issuer `https://oidc.fly.io/<org-slug>`
- Maps `sub`, `org_name`, `app_name`, `machine_name`, `aud`, `iss` claims
- Attribute condition to restrict tokens to your **org slug**
- Grants `roles/iam.workloadIdentityUser` on your **service account** to only identities from that pool with the given audience

The script will print the **AUDIENCE** string you need in the credentials JSON.

---

## 2) Build your image and deploy on Fly.io

Edit `.env.example` and `fly.toml`, then create a real `.env` or set env via `fly secrets`.

- `FLY_OIDC_AUD` should usually be: `https://oidc.fly.io/<org-slug>`
- `GOOGLE_WIF_AUDIENCE` must be the resource path printed by the setup script:
  `//iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID`

Build and deploy like normal (`fly deploy`).

---

## 3) How the runtime auth works (no keys)

1. Your app starts (`docker/start.sh`) and exports:
   - `GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-workload-identity.json`
   - `GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES=1`

2. Google auth library reads the external account JSON and executes:
   - `/app/bin/flyio_openid_token "$FLY_OIDC_AUD"` → fetches **short-lived OIDC** token from `/.fly/api`

3. The library exchanges that token at Google **STS** for a GCP access token, and **impersonates** your service account.
   - No long-lived keys. Nothing to rotate manually.

---

## 4) Smoke test in prod

Run:
```bash
python test/test_vertex.py
```

If you get a single-line response, WIF is working.

---

## Notes

- Keep `allowed-audiences` and your `FLY_OIDC_AUD` consistent.
- You can further lock down provider and impersonation with attribute conditions (e.g., match `app_name` and `sub` regex).
- If you prefer to **avoid curl**, you can rewrite `flyio_openid_token` to use a UDS-capable HTTP client; curl is simplest and tiny.

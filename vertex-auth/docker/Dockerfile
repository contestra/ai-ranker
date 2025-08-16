FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy helper, config template, scripts, test
COPY vertex-auth/app/bin /app/bin
COPY vertex-auth/config /app/config
COPY vertex-auth/scripts/render_external_account.sh /app/scripts/render_external_account.sh
COPY vertex-auth/docker/start.sh /app/start.sh
COPY vertex-auth/test /app/test

RUN chmod +x /app/bin/flyio_openid_token /app/start.sh /app/scripts/render_external_account.sh

# Auth envs (keyless WIF)
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-workload-identity.json

# Your app deps (extend as needed)
RUN pip install --no-cache-dir google-genai==0.3.0

CMD ["/app/start.sh"]

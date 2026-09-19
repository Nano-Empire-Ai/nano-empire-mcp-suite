#!/bin/bash
# Deploy the Tollbooth MCP to Google Cloud Run

PROJECT_ID="${1:-gen-lang-client-0124637641}"

echo "Building and deploying x402 Gateway to Cloud Run for project: $PROJECT_ID..."

gcloud run deploy nano-empire-mcp \
  --project "$PROJECT_ID" \
  --source . \
  --port 8404 \
  --allow-unauthenticated \
  --region us-central1 \
  --set-env-vars="PORT=8404" \
  --quiet

echo "Deploy complete! Note your service URL and update agents.json if necessary."

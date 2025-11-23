#!/bin/bash
#
# Script to create secrets in Google Secret Manager
# Usage: ./scripts/setup-secrets.sh [PROJECT_ID]
#

set -e

PROJECT_ID=${1:-"your-project-id"}

echo "🔐 Setting up secrets in Secret Manager"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create secrets
gcloud secrets create reports-app-db-host --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-db-name --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-db-user --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-db-password --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-aws-access-key --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-aws-secret-key --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-redis-host --project=${PROJECT_ID} --replication-policy="automatic" || true
gcloud secrets create reports-app-secret-key --project=${PROJECT_ID} --replication-policy="automatic" || true

echo ""
echo "✅ Secrets created!"
echo ""
echo "Now add secret values using:"
echo "  echo -n 'secret-value' | gcloud secrets versions add reports-app-db-host --data-file=-"

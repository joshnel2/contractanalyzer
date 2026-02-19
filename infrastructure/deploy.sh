#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Strapped AI — Azure Deployment Script
#
# Creates:
#   1. Resource group
#   2. Azure Database for PostgreSQL Flexible Server
#   3. Azure Web App (Python 3.12) for the web frontend
#   4. Azure Function App for email processing
#
# Prerequisites:
#   1. Azure CLI installed and logged in  (az login)
#   2. .env file populated
#
# Usage:
#   chmod +x infrastructure/deploy.sh
#   ./infrastructure/deploy.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration (edit or set via env vars) ─────────────────────────────────

RESOURCE_GROUP="${STRAPPED_RESOURCE_GROUP:-strapped-ai-rg}"
LOCATION="${STRAPPED_LOCATION:-eastus}"
WEB_APP_NAME="${STRAPPED_WEB_APP_NAME:-strapped-ai-web}"
FUNC_APP_NAME="${STRAPPED_FUNC_APP_NAME:-strapped-ai-func}"
PG_SERVER_NAME="${STRAPPED_PG_SERVER:-strapped-ai-pg}"
PG_DB_NAME="${STRAPPED_PG_DB:-strapped}"
PG_ADMIN_USER="${STRAPPED_PG_ADMIN:-strappedadmin}"
PG_ADMIN_PASS="${STRAPPED_PG_PASSWORD:-$(openssl rand -base64 24)}"
STORAGE_ACCOUNT="${STRAPPED_STORAGE_ACCOUNT:-strappedaistor}"
APP_SERVICE_PLAN="${STRAPPED_PLAN:-strapped-ai-plan}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Strapped AI — Azure Deployment                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [ -f .env ]; then
  set -a; source .env; set +a
fi

# ── 1. Resource Group ────────────────────────────────────────────────────────

echo "[1/7] Creating resource group: $RESOURCE_GROUP ..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# ── 2. PostgreSQL Flexible Server ────────────────────────────────────────────

echo "[2/7] Creating PostgreSQL Flexible Server: $PG_SERVER_NAME ..."
az postgres flexible-server create \
  --name "$PG_SERVER_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --admin-user "$PG_ADMIN_USER" \
  --admin-password "$PG_ADMIN_PASS" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --yes \
  --output none

echo "   Creating database: $PG_DB_NAME ..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$PG_SERVER_NAME" \
  --database-name "$PG_DB_NAME" \
  --output none

echo "   Allowing Azure services to connect ..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$PG_SERVER_NAME" \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0 \
  --output none

PG_HOST="${PG_SERVER_NAME}.postgres.database.azure.com"
DATABASE_URL="postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASS}@${PG_HOST}:5432/${PG_DB_NAME}?sslmode=require"

echo "   DATABASE_URL constructed."

# ── 3. Storage Account (for Function App) ────────────────────────────────────

echo "[3/7] Creating storage account: $STORAGE_ACCOUNT ..."
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --output none

# ── 4. App Service Plan ─────────────────────────────────────────────────────

echo "[4/7] Creating App Service Plan: $APP_SERVICE_PLAN ..."
az appservice plan create \
  --name "$APP_SERVICE_PLAN" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku B1 \
  --is-linux \
  --output none

# ── 5. Web App ──────────────────────────────────────────────────────────────

echo "[5/7] Creating Web App: $WEB_APP_NAME ..."
az webapp create \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$APP_SERVICE_PLAN" \
  --runtime "PYTHON:3.12" \
  --output none

az webapp config set \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-file "startup.sh" \
  --output none

az webapp config appsettings set \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}" \
    AZURE_OPENAI_DEPLOYMENT_NAME="${AZURE_OPENAI_DEPLOYMENT_NAME:-}" \
    AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}" \
    AZURE_TENANT_ID="${AZURE_TENANT_ID:-}" \
    AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}" \
    AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:-}" \
    VELA_MAILBOX="${VELA_MAILBOX:-strapped@yourcompany.com}" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  --output none

# ── 6. Function App ─────────────────────────────────────────────────────────

echo "[6/7] Creating Function App: $FUNC_APP_NAME ..."
az functionapp create \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --plan "$APP_SERVICE_PLAN" \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --os-type Linux \
  --output none

az functionapp config appsettings set \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}" \
    AZURE_OPENAI_DEPLOYMENT_NAME="${AZURE_OPENAI_DEPLOYMENT_NAME:-}" \
    AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}" \
    AZURE_TENANT_ID="${AZURE_TENANT_ID:-}" \
    AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}" \
    AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:-}" \
    VELA_MAILBOX="${VELA_MAILBOX:-strapped@yourcompany.com}" \
  --output none

az functionapp identity assign \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

# ── 7. Deploy Code ──────────────────────────────────────────────────────────

echo "[7/7] Deploying code ..."

echo "   Deploying Web App ..."
az webapp up \
  --name "$WEB_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --runtime "PYTHON:3.12" \
  --output none 2>/dev/null || echo "   (Use 'az webapp deploy' or GitHub Actions for production)"

echo "   Deploying Function App ..."
func azure functionapp publish "$FUNC_APP_NAME" --python 2>/dev/null || echo "   (Install Azure Functions Core Tools to deploy the function)"

# ── Summary ──────────────────────────────────────────────────────────────────

WEB_URL="https://${WEB_APP_NAME}.azurewebsites.net"
FUNC_URL="https://${FUNC_APP_NAME}.azurewebsites.net/api/strapped"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Deployment Complete                                     ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Web App    : $WEB_URL"
echo "║  Function   : $FUNC_URL"
echo "║  PostgreSQL : $PG_HOST"
echo "║  Database   : $PG_DB_NAME"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  PG Admin User : $PG_ADMIN_USER"
echo "  PG Admin Pass : $PG_ADMIN_PASS"
echo ""
echo "  SAVE THESE CREDENTIALS SECURELY."
echo ""
echo "Next steps:"
echo "  1. Grant Graph API permissions to the Function App Managed Identity"
echo "  2. Deploy the Logic App (see infrastructure/logic_app_template.json)"
echo "  3. Seed preferences: DATABASE_URL='$DATABASE_URL' python data/seed_preferences.py"
echo "  4. Visit $WEB_URL"

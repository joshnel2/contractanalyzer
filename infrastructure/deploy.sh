#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Vela-Law — Azure Deployment Script
#
# Prerequisites:
#   1. Azure CLI installed and logged in  (az login)
#   2. .env file populated with all required values
#   3. Python 3.12+ and pip available
#
# Usage:
#   chmod +x infrastructure/deploy.sh
#   ./infrastructure/deploy.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration (edit these) ───────────────────────────────────────────────

RESOURCE_GROUP="${VELA_RESOURCE_GROUP:-vela-law-rg}"
LOCATION="${VELA_LOCATION:-eastus}"
FUNC_APP_NAME="${VELA_FUNC_APP_NAME:-vela-law-func}"
STORAGE_ACCOUNT="${VELA_STORAGE_ACCOUNT:-velalawstorage}"
LOGIC_APP_NAME="${VELA_LOGIC_APP_NAME:-vela-law-email-trigger}"
SHARED_MAILBOX="${VELA_MAILBOX:-vela@ourfirm.onmicrosoft.com}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Vela-Law Azure Deployment                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Resource Group ───────────────────────────────────────────────────

echo "[1/6] Creating resource group: $RESOURCE_GROUP ..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ── Step 2: Storage Account ─────────────────────────────────────────────────

echo "[2/6] Creating storage account: $STORAGE_ACCOUNT ..."
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --output none

STORAGE_CONN=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString \
  --output tsv)

echo "   Storage connection string retrieved."

# ── Step 3: Function App ────────────────────────────────────────────────────

echo "[3/6] Creating Function App: $FUNC_APP_NAME ..."
az functionapp create \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --storage-account "$STORAGE_ACCOUNT" \
  --consumption-plan-location "$LOCATION" \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --os-type Linux \
  --output none

# ── Step 4: Configure App Settings ──────────────────────────────────────────

echo "[4/6] Configuring app settings ..."

# Source .env if available
if [ -f .env ]; then
  set -a; source .env; set +a
fi

az functionapp config appsettings set \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}" \
    AZURE_OPENAI_DEPLOYMENT_NAME="${AZURE_OPENAI_DEPLOYMENT_NAME:-}" \
    AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}" \
    AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
    AZURE_TENANT_ID="${AZURE_TENANT_ID:-}" \
    AZURE_CLIENT_ID="${AZURE_CLIENT_ID:-}" \
    AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:-}" \
    VELA_MAILBOX="$SHARED_MAILBOX" \
    VELA_LOG_LEVEL="${VELA_LOG_LEVEL:-INFO}" \
    VELA_AUTO_APPROVE_THRESHOLD="${VELA_AUTO_APPROVE_THRESHOLD:-85}" \
    VELA_DEFAULT_TIMEZONE="${VELA_DEFAULT_TIMEZONE:-America/New_York}" \
  --output none

# ── Step 5: Enable Managed Identity ─────────────────────────────────────────

echo "[5/6] Enabling system-assigned Managed Identity ..."
az functionapp identity assign \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output none

IDENTITY_ID=$(az functionapp identity show \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query principalId \
  --output tsv)

echo "   Managed Identity principal: $IDENTITY_ID"
echo ""
echo "   IMPORTANT: Grant this identity the following Graph permissions:"
echo "     - Calendars.ReadWrite"
echo "     - Mail.Send"
echo "     - User.Read.All"
echo ""
echo "   Use the Azure Portal > Entra ID > Enterprise Applications >"
echo "   find the Managed Identity > Permissions > Grant admin consent."

# ── Step 6: Deploy Function Code ────────────────────────────────────────────

echo "[6/6] Deploying function code ..."
func azure functionapp publish "$FUNC_APP_NAME" --python

# ── Summary ──────────────────────────────────────────────────────────────────

FUNC_URL="https://${FUNC_APP_NAME}.azurewebsites.net/api/vela"
FUNC_KEY=$(az functionapp keys list \
  --name "$FUNC_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "functionKeys.default" \
  --output tsv 2>/dev/null || echo "<retrieve-from-portal>")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Deployment Complete                                     ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Function URL : $FUNC_URL"
echo "║  Function Key : $FUNC_KEY"
echo "║  Storage Acct : $STORAGE_ACCOUNT"
echo "║  Resource Grp : $RESOURCE_GROUP"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Grant Graph API permissions to the Managed Identity"
echo "  2. Deploy the Logic App (see infrastructure/logic_app_template.json)"
echo "  3. Seed preferences: python data/seed_preferences.py"
echo "  4. Send a test email to $SHARED_MAILBOX"

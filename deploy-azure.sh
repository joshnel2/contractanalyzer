#!/bin/bash

# Azure Deployment Script for Attorney Commission Calculator
# Run this script to deploy to Azure App Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Attorney Commission Calculator - Azure Deploy${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed.${NC}"
    echo "Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Logging in...${NC}"
    az login
fi

# Configuration - modify these values
RESOURCE_GROUP="${RESOURCE_GROUP:-commission-calculator-rg}"
LOCATION="${LOCATION:-eastus}"
APP_NAME="${APP_NAME:-commission-calculator-$(date +%s)}"
APP_SERVICE_PLAN="${APP_SERVICE_PLAN:-commission-calc-plan}"
SKU="${SKU:-B1}"

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  App Name: $APP_NAME"
echo "  App Service Plan: $APP_SERVICE_PLAN"
echo "  SKU: $SKU"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Create resource group
echo -e "${GREEN}Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service plan
echo -e "${GREEN}Creating App Service plan...${NC}"
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --sku $SKU \
    --is-linux

# Create web app
echo -e "${GREEN}Creating Web App...${NC}"
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --name $APP_NAME \
    --runtime "PYTHON:3.11"

# Configure startup command
echo -e "${GREEN}Configuring startup command...${NC}"
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout=600 --workers=2 app:app"

# Prompt for Azure OpenAI settings
echo ""
echo -e "${YELLOW}Enter your Azure OpenAI settings:${NC}"
read -p "Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com/): " AZURE_ENDPOINT
read -p "Azure OpenAI API Key: " AZURE_KEY
read -p "Azure OpenAI Deployment Name: " AZURE_DEPLOYMENT

# Set environment variables
echo -e "${GREEN}Setting environment variables...${NC}"
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
    AZURE_OPENAI_ENDPOINT="$AZURE_ENDPOINT" \
    AZURE_OPENAI_API_KEY="$AZURE_KEY" \
    AZURE_OPENAI_DEPLOYMENT="$AZURE_DEPLOYMENT" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Deploy the application
echo -e "${GREEN}Deploying application...${NC}"
az webapp up \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --runtime "PYTHON:3.11"

# Get the URL
APP_URL="https://${APP_NAME}.azurewebsites.net"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Your app is live at: ${YELLOW}$APP_URL${NC}"
echo ""
echo "To view logs:"
echo "  az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME"
echo ""
echo "To update the app later:"
echo "  az webapp up --resource-group $RESOURCE_GROUP --name $APP_NAME"

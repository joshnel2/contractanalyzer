# Moltbot Azure AI Bridge (Azure Functions)

Serverless bridge connecting Moltbot to Azure AI Foundry.

## Deploy to Azure Functions

### Option 1: Azure Portal (Easiest)

1. Go to **Azure Portal** → **Create a resource** → **Function App**
2. Settings:
   - **Runtime stack**: Python
   - **Version**: 3.11
   - **Plan type**: Consumption (serverless)
3. After creation, go to your Function App
4. **Deployment Center** → **GitHub** → Select this repo → Save
5. **Configuration** → **Application settings** → Add:
   - `AZURE_OPENAI_KEY` = your key
   - `AZURE_OPENAI_ENDPOINT` = `https://your-resource.openai.azure.com`
   - `AZURE_DEPLOYMENT_NAME` = your deployment name

### Option 2: VS Code

1. Install **Azure Functions** extension
2. Open this folder
3. Click Azure icon → Functions → Deploy to Function App

## Configure Moltbot

Set API endpoint to:
```
https://your-function-app.azurewebsites.net/api
```

## Endpoints

- `GET /api/` - Health check
- `POST /api/v1/chat/completions` - Main endpoint
- `POST /api/chat/completions` - Alternative

## Note

Streaming is disabled in Azure Functions. Responses return complete (not typed out character by character). If you need streaming, use Azure Web App with the Flask version.

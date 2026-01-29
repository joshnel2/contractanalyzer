# Moltbot Azure AI Bridge

Connects Moltbot to Azure AI Foundry. Translates authentication and streams responses.

## Azure Web App Deployment

### Environment Variables

In Azure Portal → Web App → **Configuration** → **Application settings**, add:

| Name | Value |
|------|-------|
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com` |
| `AZURE_DEPLOYMENT_NAME` | Your deployment name (e.g., gpt-4o) |

### Startup Command

Leave the Startup Command **empty**. Azure auto-detects Flask apps.

If it still doesn't work, try setting Startup Command to:
```
gunicorn app:app
```

## Configure Moltbot

Set API endpoint to your Azure Web App URL:
```
https://your-app.azurewebsites.net
```

## Endpoints

- `GET /` - Health check (returns `{"status": "Bridge Active"}`)
- `POST /v1/chat/completions` - Main endpoint (Moltbot default)
- `POST /chat/completions` - Alternative endpoint

## Local Development

```bash
pip install -r requirements.txt
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_DEPLOYMENT_NAME="your-deployment"
python app.py
```

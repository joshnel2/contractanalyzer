# Moltbot Azure AI Bridge

Connects Moltbot to Azure AI Foundry. Translates authentication and streams responses.

## Deploy to Railway (Recommended)

1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select this repo
4. Add environment variables:
   - `AZURE_OPENAI_KEY` - Your Azure OpenAI key
   - `AZURE_OPENAI_ENDPOINT` - e.g. `https://your-resource.openai.azure.com`
   - `AZURE_DEPLOYMENT_NAME` - Your deployment name
5. Railway auto-deploys. Get your URL from the dashboard.

## Configure Moltbot

Set API endpoint to your Railway URL:
```
https://your-app.up.railway.app
```

## Endpoints

- `GET /` - Health check
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

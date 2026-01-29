# MOLT Bot Azure AI Foundry Bridge

Connects MOLT Bot to Azure AI Foundry by providing an OpenAI-compatible API endpoint.

## Required Environment Variables

Set these in your Azure Function App → Configuration → Application settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Your AI Foundry or Azure OpenAI endpoint URL | `https://your-resource.openai.azure.com` |
| `AZURE_AI_FOUNDRY_API_KEY` | Your API key from Azure AI Foundry | `abc123...` |
| `AZURE_AI_FOUNDRY_DEPLOYMENT` | The name of your model deployment | `gpt-4o` |
| `AZURE_AI_API_VERSION` | (Optional) API version | `2024-08-01-preview` |

### Finding Your Azure AI Foundry Values

1. **Endpoint**: In Azure AI Foundry portal, go to your project → Deployments → Select your model → Copy the "Target URI" (just the base URL part)
2. **API Key**: Same location → Copy "Key"
3. **Deployment Name**: The name you gave your model deployment (e.g., `gpt-4o`, `gpt-4o-mini`)

### Legacy Azure OpenAI Variables (Also Supported)

The bridge also supports these legacy variable names:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_KEY`
- `AZURE_DEPLOYMENT_NAME`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check - shows configuration status |
| `/v1/chat/completions` | POST | Main chat completions endpoint |
| `/chat/completions` | POST | Alternative (without v1 prefix) |
| `/v1/models` | GET | List available models |
| `/models` | GET | Alternative (without v1 prefix) |

## Configure MOLT Bot

In MOLT Bot settings, set:
- **API Endpoint**: `https://moltazureai.azurewebsites.net`
- **API Key**: Can be any value (authentication is handled by the bridge)

## Deployment

This function app auto-deploys from GitHub to Azure Functions via GitHub Actions when you push to `main`.

## Testing

Test the health endpoint:
```bash
curl https://moltazureai.azurewebsites.net/
```

Should return:
```json
{
  "status": "Bridge Active",
  "endpoint_configured": true,
  "api_key_configured": true,
  "deployment_configured": true
}
```

Test chat completions:
```bash
curl -X POST https://moltazureai.azurewebsites.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

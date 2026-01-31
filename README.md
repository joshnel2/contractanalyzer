# MoltBot Azure AI Foundry Bridge

An Azure Function app that provides an OpenAI-compatible API endpoint for connecting **MoltBot** (or any OpenAI-compatible client) to **Azure AI Foundry**.

This allows you to use Azure-hosted models (GPT-4o, GPT-4o-mini, GPT-5-mini, etc.) with MoltBot.

## How It Works

```
MoltBot → This Azure Function → Azure AI Foundry → Your deployed model
       (OpenAI format)         (Azure format)      (GPT-4o, etc.)
```

The function translates OpenAI-compatible API requests to Azure AI Foundry format.

## Required Environment Variables

Set these in your Azure Function App → Configuration → Application settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI / AI Foundry endpoint URL | `https://your-resource.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | Your API key | `abc123...` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | The name of your model deployment | `gpt-5-mini` |
| `AZURE_AI_API_VERSION` | (Optional) API version | `2024-08-01-preview` |

### Finding Your Azure Values

1. **Endpoint**: In Azure AI Foundry portal → Your project → Deployments → Select your model → Copy the "Target URI" (just the base URL, e.g., `https://your-resource.openai.azure.com`)
2. **API Key**: Same location → Copy "Key"
3. **Deployment Name**: The name you gave your model deployment (e.g., `gpt-4o`, `gpt-4o-mini`)

## MoltBot Configuration

### Configuration File Location

Your MoltBot config file is typically at:
- `~/.moltbot/moltbot.json` (JSON format)
- `~/.moltbot/moltbot.json5` (JSON5 format - allows comments)

---

## Quick Start Configuration

Add this to your MoltBot config file to use the Azure bridge:

```json
{
  "providers": {
    "azure-bridge": {
      "type": "openai",
      "baseUrl": "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1",
      "apiKey": "any-value",
      "models": ["gpt-5-mini"]
    }
  },
  "defaultModel": "azure-bridge:gpt-5-mini"
}
```

### Alternative Configuration Formats

If the above doesn't work, try one of these formats:

**Format A - Simple provider:**
```json
{
  "openaiBaseUrl": "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1",
  "openaiApiKey": "any-value",
  "model": "gpt-5-mini"
}
```

**Format B - Custom provider with full options:**
```json
{
  "models": {
    "providers": {
      "azure-bridge": {
        "baseUrl": "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1",
        "apiKey": "any-value",
        "api": "openai-completions",
        "models": [
          {
            "id": "gpt-5-mini",
            "name": "GPT-5-mini via Azure"
          }
        ]
      }
    }
  }
}
```

**Format C - Claude Code / Roo Code style:**
```json
{
  "apiProvider": "openai-compatible",
  "openAiBaseUrl": "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1",
  "openAiApiKey": "any-value", 
  "openAiModelId": "gpt-5-mini"
}
```

---

## Direct Azure OpenAI Connection (Alternative)

If you want MoltBot to connect directly to Azure OpenAI (without this bridge), use:

```json
{
  "apiProvider": "openai-compatible",
  "openAiBaseUrl": "https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT/",
  "openAiApiKey": "YOUR_AZURE_API_KEY",
  "openAiModelId": "gpt-5-mini"
}
```

Or with Azure-specific headers:
```json
{
  "providers": {
    "azure-direct": {
      "type": "azure-openai",
      "endpoint": "https://YOUR-RESOURCE.openai.azure.com",
      "apiKey": "YOUR_AZURE_API_KEY",
      "deploymentName": "gpt-5-mini",
      "apiVersion": "2024-08-01-preview"
    }
  }
}
```

### Finding Your Azure Values

1. Go to [Azure AI Foundry](https://ai.azure.com) or Azure Portal
2. Navigate to your Azure OpenAI resource
3. **Endpoint**: Copy from "Keys and Endpoint" section
4. **API Key**: Copy from "Keys and Endpoint" section  
5. **Deployment Name**: The name you gave your model deployment

---

## Debugging Configuration Issues

### Test the endpoints directly:

```bash
# 1. Test models endpoint
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1/models

# 2. Test chat completion
curl -X POST https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'

# 3. Debug endpoint - shows what the server receives
curl -X POST https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/debug \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{"test": "data"}'
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "unknown agent" | Model ID not matching | Make sure `model` or `openAiModelId` is exactly `gpt-5-mini` |
| 400 Bad Request | Invalid request format | Check the debug endpoint to see what's being sent |
| 404 Not Found | Wrong URL | Make sure baseUrl ends with `/v1` (not `/v1/`) |
| Connection refused | Wrong endpoint | Verify the full URL is correct |

### Check what MoltBot is sending:

Use the debug endpoint in your config to see the actual requests:
```json
{
  "openAiBaseUrl": "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net",
  "openAiApiKey": "debug",
  "openAiModelId": "debug"
}
```
Then check the Azure Function logs to see what's received.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check - shows configuration status |
| `/v1/chat/completions` | POST | Main chat completions endpoint (OpenAI format) |
| `/chat/completions` | POST | Alternative (without v1 prefix) |
| `/v1/models` | GET | List available models |
| `/models` | GET | Alternative (without v1 prefix) |
| `/debug` | GET/POST | Debug endpoint - echoes request details |

## Testing

### List Models

```bash
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1/models
```

Expected response:
```json
{
  "object": "list",
  "data": [{"id": "gpt-5-mini", "object": "model", ...}]
}
```

### Chat Completion

```bash
curl -X POST https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'
```

### Debug Endpoint

```bash
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/debug
```

This returns details about the request and server configuration - useful for troubleshooting.

## Deployment

This function app auto-deploys from GitHub to Azure Functions via GitHub Actions when you push to `main`.

### Manual Deployment

1. Create an Azure Function App (Python 3.11+, Linux)
2. Set the environment variables in Configuration
3. Deploy via:
   - VS Code Azure Functions extension
   - Azure CLI: `func azure functionapp publish your-app-name`
   - GitHub Actions (already configured in `.github/workflows/`)

## Troubleshooting

### "Server not configured" errors

Make sure all three environment variables are set in Azure:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

### "unknown agent" error

This usually means the model ID in your config doesn't match what's available. Try:
1. Make sure your model ID is exactly `gpt-5-mini` (or whatever the deployment name is)
2. Use the debug endpoint to check what's being sent
3. Try a simpler configuration format (see Quick Start above)

### 400 Bad Request errors

1. Check the request format - use the debug endpoint to see what's being received
2. Make sure `baseUrl` ends with `/v1` (no trailing slash)
3. Verify the model ID is correct

### Timeout errors

Azure AI Foundry requests can take time. The function has a 5-minute timeout. If hitting timeouts:
1. Check if the model deployment is active in Azure
2. Try a smaller prompt
3. Consider using a faster model (e.g., `gpt-4o-mini`)

### "Model not found" in Azure

Make sure your `AZURE_OPENAI_DEPLOYMENT_NAME` matches exactly the name in Azure AI Foundry.

### MoltBot can't connect

1. Verify the URL is correct: `https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1`
2. Test the endpoint: `curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/v1/models`
3. Make sure `baseUrl` ends with `/v1` (not `/v1/`)
4. Try a different config format from the options above

## Links

- [Azure AI Foundry](https://ai.azure.com)
- [Azure OpenAI Service](https://azure.microsoft.com/products/ai-services/openai-service)

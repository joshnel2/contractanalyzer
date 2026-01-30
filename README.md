# Moltbot Azure AI Foundry Bridge

An Azure Function app that provides an OpenAI-compatible API endpoint for connecting **Moltbot** (clawd.bot) to **Azure AI Foundry**.

This allows you to use Azure-hosted models (GPT-4o, GPT-4o-mini, etc.) with Moltbot instead of direct Anthropic or OpenAI API keys.

## How It Works

```
Moltbot → This Azure Function → Azure AI Foundry → Your deployed model
       (OpenAI format)        (Azure format)      (GPT-4o, etc.)
```

The function translates OpenAI-compatible API requests to Azure AI Foundry format, enabling Moltbot to use your Azure-hosted models.

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

## Moltbot Configuration

Add this to your `~/.moltbot/moltbot.json` (or `moltbot.json5`):

```json5
{
  // Use the Azure bridge as your model provider
  agents: {
    defaults: {
      model: { primary: "azure-foundry/gpt-5-mini" }
    }
  },
  
  // Configure the custom Azure provider
  models: {
    mode: "merge",
    providers: {
      "azure-foundry": {
        baseUrl: "https://your-function-app.azurewebsites.net/v1",
        apiKey: "not-needed",  // Auth handled by the bridge
        api: "openai-completions",
        models: [
          {
            id: "gpt-5-mini",
            name: "GPT-5-mini via Azure",
            reasoning: false,
            input: ["text", "image"],
            contextWindow: 128000,
            maxTokens: 16384
          }
        ]
      }
    }
  }
}
```

### Minimal Configuration

If you just want to quickly test, the simplest config is:

```json5
{
  agents: {
    defaults: {
      model: { primary: "azure-foundry/gpt-5-mini" }
    }
  },
  models: {
    providers: {
      "azure-foundry": {
        baseUrl: "https://moltazureai.azurewebsites.net/v1",
        apiKey: "any-value",
        api: "openai-completions",
        models: [{ id: "gpt-5-mini", name: "GPT-5-mini" }]
      }
    }
  }
}
```

### Using with Other Providers (Failover)

You can configure this as a fallback provider:

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "anthropic/claude-opus-4-5",
        fallback: ["azure-foundry/gpt-5-mini"]
      }
    }
  },
  models: {
    mode: "merge",
    providers: {
      "azure-foundry": {
        baseUrl: "https://your-function-app.azurewebsites.net/v1",
        apiKey: "not-needed",
        api: "openai-completions",
        models: [{ id: "gpt-5-mini", name: "GPT-5-mini via Azure" }]
      }
    }
  }
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check - shows configuration status |
| `/v1/chat/completions` | POST | Main chat completions endpoint (OpenAI format) |
| `/chat/completions` | POST | Alternative (without v1 prefix) |
| `/v1/models` | GET | List available models |
| `/models` | GET | Alternative (without v1 prefix) |

## Testing

### Health Check

```bash
curl https://your-function-app.azurewebsites.net/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Azure AI Foundry Bridge for Moltbot",
  "version": "1.0.0",
  "endpoint_configured": true,
  "api_key_configured": true,
  "deployment_configured": true,
  "deployment_name": "gpt-5-mini"
}
```

### List Models

```bash
curl https://your-function-app.azurewebsites.net/v1/models
```

### Chat Completion

```bash
curl -X POST https://your-function-app.azurewebsites.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any-key" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

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

### Timeout errors

Azure AI Foundry requests can take time. The function has a 5-minute timeout configured. If you're hitting timeouts:
1. Check if the model deployment is active in Azure
2. Try a smaller prompt
3. Consider using a faster model (e.g., `gpt-4o-mini`)

### "Model not found" in Azure

Make sure your `AZURE_OPENAI_DEPLOYMENT_NAME` matches exactly the name shown in Azure AI Foundry deployments.

### Moltbot can't connect

1. Verify the function app URL is correct
2. Check if the function app is running: `curl https://your-app.azurewebsites.net/`
3. Ensure your `moltbot.json` has the correct `baseUrl` (include `/v1` at the end)

## Links

- [Moltbot Documentation](https://docs.molt.bot)
- [Moltbot Model Providers](https://docs.molt.bot/concepts/model-providers)
- [Azure AI Foundry](https://ai.azure.com)
- [Azure OpenAI Service](https://azure.microsoft.com/products/ai-services/openai-service)

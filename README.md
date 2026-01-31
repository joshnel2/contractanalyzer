# Clawdbot Azure AI Foundry Bridge

An Azure Function app that provides an OpenAI-compatible API endpoint for connecting **Clawdbot** to **Azure AI Foundry**.

This allows you to use Azure-hosted models (GPT-4o, GPT-4o-mini, GPT-5-mini, etc.) with Clawdbot instead of direct Anthropic or OpenAI API keys.

## How It Works

```
Clawdbot → This Azure Function → Azure AI Foundry → Your deployed model
        (OpenAI format)         (Azure format)      (GPT-4o, etc.)
```

The function translates OpenAI-compatible API requests to Azure AI Foundry format, enabling Clawdbot to use your Azure-hosted models.

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

## Clawdbot Configuration

There are two ways to connect Clawdbot to Azure OpenAI:

| Method | When to Use |
|--------|-------------|
| **Direct Connection** | You want Clawdbot to connect directly to Azure OpenAI (simpler setup) |
| **Via This Bridge** | You need a proxy, want to hide API keys from clients, or need request transformation |

### Configuration File Location

Your Clawdbot config file is located at one of these paths:
- `~/.clawdbot/clawdbot.json` (JSON format)
- `~/.clawdbot/clawdbot.json5` (JSON5 format - allows comments)
- `~/.moltbot/moltbot.json` (legacy path)

---

## Option 1: Direct Azure OpenAI Connection (Recommended)

If you just want Clawdbot to use Azure OpenAI directly, use this configuration:

```json5
{
  "models": {
    "mode": "merge",
    "providers": {
      "azure": {
        "api": "openai-completions",
        "baseUrl": "https://YOUR-RESOURCE.openai.azure.com/openai/v1/",
        "apiKey": "YOUR_AZURE_API_KEY",
        "apiVersion": "2024-08-01-preview",
        "models": [
          {
            "id": "gpt-5.1-chat",
            "name": "GPT-5.1 Chat (Azure)",
            "contextWindow": 128000
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "azure:default/gpt-5.1-chat",
        "fallbacks": ["azure:default/gpt-5.1-chat"]
      }
    }
  }
}
```

### Direct Connection Fields

| Field | Description |
|-------|-------------|
| `api` | Use `"openai-completions"` for Azure OpenAI |
| `baseUrl` | Your Azure OpenAI endpoint + `/openai/v1/` |
| `apiKey` | Your Azure OpenAI API key |
| `apiVersion` | Azure API version (e.g., `"2024-08-01-preview"`) |
| `models[].id` | Your deployment name in Azure |
| Model reference | Format: `azure:default/DEPLOYMENT_NAME` |

### Finding Your Azure Values

1. Go to [Azure AI Foundry](https://ai.azure.com) or Azure Portal
2. Navigate to your Azure OpenAI resource
3. **Endpoint**: Copy from "Keys and Endpoint" section (add `/openai/v1/` to the end)
4. **API Key**: Copy from "Keys and Endpoint" section
5. **Deployment Name**: The name you gave your model deployment (e.g., `gpt-5.1-chat`)

---

## Option 2: Via This Azure Bridge

Use the bridge when you want to:
- Hide Azure credentials from the client (the bridge handles auth)
- Add a proxy layer between Clawdbot and Azure
- Use Azure Functions for request logging/transformation

### Bridge Configuration Example

Add this to your config file:

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
        baseUrl: "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1",
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

### Configuration Breakdown

Here's what each field means:

| Field | Description |
|-------|-------------|
| `agents.defaults.model.primary` | The default model to use, in format `provider/model-id` |
| `models.mode` | Set to `"merge"` to add this provider alongside existing ones |
| `models.providers.azure-foundry` | The name of your custom provider (can be anything) |
| `baseUrl` | Your Azure Function URL + `/api/v1` |
| `apiKey` | Can be any value (authentication is handled by the bridge) |
| `api` | Must be `"openai-completions"` for this bridge |
| `models` | Array of available models with their capabilities |

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
        baseUrl: "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1",
        apiKey: "any-value",
        api: "openai-completions",
        models: [{ id: "gpt-5-mini", name: "GPT-5-mini" }]
      }
    }
  }
}
```

### Using with Other Providers (Failover)

You can configure this as a fallback provider while keeping Claude as your primary:

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
        baseUrl: "https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1",
        apiKey: "not-needed",
        api: "openai-completions",
        models: [{ id: "gpt-5-mini", name: "GPT-5-mini via Azure" }]
      }
    }
  }
}
```

### Step-by-Step Setup

1. **Locate your config file**: Check `~/.clawdbot/clawdbot.json5` or create it if it doesn't exist

2. **Add the provider configuration**: Copy one of the examples above into your config file

3. **Customize the model ID**: Change `gpt-5-mini` to match your Azure deployment name (set in `AZURE_OPENAI_DEPLOYMENT_NAME`)

4. **Update the baseUrl**: If you deployed your own instance, replace the URL with your Azure Function App URL

5. **Restart Clawdbot**: The new provider will be available immediately

### Verifying Your Configuration

After configuring, you can verify the bridge is working:

```bash
# Check the health endpoint
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/

# Test a simple completion
curl -X POST https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5-mini", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | Health check - shows configuration status |
| `/api/v1/chat/completions` | POST | Main chat completions endpoint (OpenAI format) |
| `/api/chat/completions` | POST | Alternative (without v1 prefix) |
| `/api/v1/models` | GET | List available models |
| `/api/models` | GET | Alternative (without v1 prefix) |

## Testing

### Health Check

```bash
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Azure AI Foundry Bridge for Clawdbot",
  "version": "1.0.0",
  "endpoint_configured": true,
  "api_key_configured": true,
  "deployment_configured": true,
  "deployment_name": "gpt-5-mini"
}
```

### List Models

```bash
curl https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1/models
```

### Chat Completion

```bash
curl -X POST https://moltazureai-a8agahhybjdre5c4.canadacentral-01.azurewebsites.net/api/v1/chat/completions \
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

### Clawdbot can't connect

1. Verify the function app URL is correct
2. Check if the function app is running: `curl https://your-app.azurewebsites.net/api/`
3. Ensure your `clawdbot.json5` has the correct `baseUrl` (include `/api/v1` at the end)
4. Check that the provider name in your config matches what you're using (e.g., `azure-foundry`)

## Links

- [Clawdbot Documentation](https://docs.clawd.bot)
- [Clawdbot Model Providers](https://docs.clawd.bot/concepts/model-providers)
- [Azure AI Foundry](https://ai.azure.com)
- [Azure OpenAI Service](https://azure.microsoft.com/products/ai-services/openai-service)

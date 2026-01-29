# Moltbot Azure AI Bridge

A professional Python FastAPI bridge designed to connect Moltbot (formerly Clawdbot) to Azure AI Foundry. This application translates OpenAI-style API requests to Azure OpenAI format with full streaming support.

## Features

- **Authentication Translation**: Automatically converts Bearer token authentication to Azure's `api-key` format
- **SSE Streaming**: Full support for Server-Sent Events enabling real-time typing effects in Moltbot
- **Health Checks**: Built-in health endpoint for Azure Web App deployment verification
- **Error Handling**: Graceful error handling with clear error messages
- **Logging**: Comprehensive logging for Azure Log Stream monitoring

## Environment Variables

Set the following environment variables in your Azure Web App configuration:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI endpoint URL (e.g., `https://your-resource.openai.azure.com`) |
| `AZURE_DEPLOYMENT_NAME` | Your Azure OpenAI deployment name |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check - returns `{"status": "Bridge Active"}` |
| POST | `/v1/chat/completions` | Main chat completions endpoint (Moltbot default) |
| POST | `/chat/completions` | Alternative endpoint without `/v1` prefix |

## Deployment to Azure Web App

### 1. Create Azure Web App

Create a new Azure Web App with:
- **Runtime**: Python 3.11 or higher
- **Operating System**: Linux

### 2. Configure Environment Variables

In the Azure Portal, navigate to your Web App:
1. Go to **Settings** > **Configuration**
2. Add the following Application Settings:
   - `AZURE_OPENAI_KEY`: Your Azure OpenAI API key
   - `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint
   - `AZURE_DEPLOYMENT_NAME`: Your deployment name

### 3. Configure Startup Command

In the Azure Portal:
1. Go to **Settings** > **Configuration** > **General settings**
2. Set the **Startup Command** to:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
```

### 4. Deploy the Application

Deploy using one of these methods:
- **GitHub Actions**: Connect your repository for automatic deployments
- **Azure CLI**: Use `az webapp up`
- **VS Code**: Use the Azure App Service extension
- **ZIP Deploy**: Upload a ZIP file containing the application

## Local Development

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Set environment variables
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_DEPLOYMENT_NAME="your-deployment"

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or with Gunicorn (production-like):

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Testing the Bridge

```bash
# Health check
curl http://localhost:8000/

# Chat completion (non-streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Chat completion (streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Moltbot Configuration

In your Moltbot settings, configure the custom API endpoint:

- **API Endpoint**: `https://your-azure-webapp.azurewebsites.net`
- Moltbot automatically appends `/v1` to the endpoint

## Troubleshooting

### Common Issues

1. **500 Error - Missing Environment Variables**
   - Ensure all three environment variables are configured in Azure
   - Check Azure Log Stream for specific missing variable names

2. **502 Bad Gateway**
   - Verify your Azure OpenAI endpoint is correct
   - Check if the deployment name matches your Azure OpenAI deployment

3. **504 Gateway Timeout**
   - The request to Azure OpenAI is taking too long
   - Consider increasing timeout settings

### Viewing Logs

In the Azure Portal:
1. Go to your Web App
2. Navigate to **Monitoring** > **Log stream**
3. View real-time logs including "Moltbot connecting..." and "Relaying to Azure..." messages

## License

MIT License

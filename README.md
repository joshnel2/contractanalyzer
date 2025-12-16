# Attorney Commission Calculator

AI-powered commission calculator deployed on Azure.

## Setup

Set these environment variables in your Azure Web App:

| Variable | Value |
|----------|-------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Your API key |
| `AZURE_OPENAI_DEPLOYMENT` | Your model name (e.g., `gpt-4o`) |

## How It Works

1. Paste your Case Data CSV
2. Paste your Rules Sheet CSV
3. Click Calculate - AI does the math
4. Download results

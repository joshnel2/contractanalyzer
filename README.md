# Attorney Commission Calculator

AI-powered commission calculator deployed on Azure.

## Setup

### 1. Add Publish Profile to GitHub

1. Go to **Azure Portal** → **App Services** → **paymentcalculator**
2. Click **Download publish profile**
3. Go to **GitHub repo** → **Settings** → **Secrets and variables** → **Actions**
4. Add secret: `AZURE_WEBAPP_PUBLISH_PROFILE` = paste the entire file contents

### 2. Set Environment Variables in Azure

Go to **Azure Portal** → **App Services** → **paymentcalculator** → **Configuration** → **Application settings**

Add these:

| Name | Value |
|------|-------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Your API key |
| `AZURE_OPENAI_DEPLOYMENT` | Your model name (e.g., `gpt-4o`) |

Click **Save**.

## How It Works

1. Paste your Case Data CSV
2. Paste your Rules Sheet CSV  
3. Click Calculate - AI does the math
4. Download results

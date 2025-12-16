# Attorney Commission Calculator

A web application that calculates attorney commissions using Azure AI Foundry. Upload your case data and rules sheets, and the AI will carefully process each row to calculate commissions.

![Screenshot](https://via.placeholder.com/800x400?text=Attorney+Commission+Calculator)

## Features

- 📊 **Web Interface** - Drag & drop CSV upload
- 🤖 **Azure AI Powered** - Uses Azure OpenAI for accurate calculations
- 📦 **Batch Processing** - Handles large datasets by processing in batches
- ⬇️ **CSV Export** - Download results as CSV

## Quick Start

### 1. Prerequisites

- Python 3.11+ or Docker
- Azure OpenAI resource with a deployed model

### 2. Azure AI Foundry Setup

1. Go to [Azure AI Foundry](https://ai.azure.com/) or Azure Portal
2. Create an Azure OpenAI resource
3. Deploy a model (e.g., `gpt-4`, `gpt-4o`, or `gpt-35-turbo`)
4. Note down:
   - **Endpoint**: `https://your-resource.openai.azure.com/`
   - **API Key**: Found in "Keys and Endpoint"
   - **Deployment Name**: The name you gave your deployment

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your Azure credentials:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

### 4. Run the Application

**Option A: Docker (Recommended)**

```bash
docker-compose up --build
```

**Option B: Python**

```bash
pip install -r requirements.txt
python app.py
```

### 5. Open the App

Go to: **http://localhost:5000**

## How It Works

### Input Files

**Case Data CSV:**
```csv
matter,date,total collected,user,originator
Case-001,2024-01-15,10000.00,John Smith,John Smith
Case-002,2024-01-20,25000.00,Jane Doe,John Smith
```

**Rules Sheet CSV:**
```csv
attorney name,user percentage,own origination other work percentage
John Smith,30%,10%
Jane Doe,25%,15%
```

### Calculation Logic

**Agent 1 - User Calculation:**
```
User Pay = Total Collected × User Percentage
```

**Agent 2 - Originator Calculation:**
- If `user == originator`: Leave originator fields **blank**
- If `user != originator`:
  ```
  Originator Pay = User Pay × Own Origination Other Work Percentage
  ```
  ⚠️ **Critical:** Multiplies against User Pay, NOT total collected

### Output

```csv
matter,date,user,originator,total collected,user percentage,user pay,originator percentage,originator pay
Case-001,2024-01-15,John Smith,John Smith,10000.00,30.0%,3000.00,,
Case-002,2024-01-20,Jane Doe,John Smith,25000.00,25.0%,6250.00,10.0%,625.00
```

## Deployment

### Deploy to Azure App Service

```bash
# Login to Azure
az login

# Create resource group
az group create --name commission-calc-rg --location eastus

# Create App Service plan
az appservice plan create --name commission-calc-plan --resource-group commission-calc-rg --sku B1 --is-linux

# Create web app
az webapp create --resource-group commission-calc-rg --plan commission-calc-plan --name your-app-name --runtime "PYTHON:3.11"

# Configure environment variables
az webapp config appsettings set --resource-group commission-calc-rg --name your-app-name --settings \
  AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  AZURE_OPENAI_API_KEY="your-key" \
  AZURE_OPENAI_DEPLOYMENT="your-deployment"

# Deploy
az webapp up --resource-group commission-calc-rg --name your-app-name
```

### Deploy to Railway/Render

1. Push this repo to GitHub
2. Connect to Railway/Render
3. Set environment variables in dashboard
4. Deploy

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | Deployment/model name |
| `AZURE_OPENAI_API_VERSION` | ❌ | API version (default: 2024-02-15-preview) |
| `SECRET_KEY` | ❌ | Flask secret key |
| `FLASK_DEBUG` | ❌ | Enable debug mode (true/false) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/process` | POST | Process CSV files (multipart form) |
| `/health` | GET | Health check |

## File Structure

```
.
├── app.py                 # Flask application
├── templates/
│   └── index.html         # Web interface
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker build
├── docker-compose.yml    # Docker Compose config
├── .env.example          # Environment template
└── README.md
```

## Large Dataset Handling

The application processes data in batches of 20 rows to ensure:
- Accurate calculations for each row
- Rate limit compliance with Azure OpenAI
- Memory efficiency for large files

For very large datasets (1000+ rows), expect processing to take a few minutes.

## License

MIT

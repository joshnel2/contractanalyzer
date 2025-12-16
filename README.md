# Attorney Commission Calculator

A web application that calculates attorney commissions using Azure AI Foundry. Upload your case data and rules sheets, and the AI will carefully process each row to calculate commissions.

## Features

- 📊 **Web Interface** - Drag & drop CSV upload
- 🤖 **Azure AI Powered** - Uses Azure OpenAI for accurate calculations
- 📦 **Batch Processing** - Handles large datasets by processing in batches
- ⬇️ **CSV Export** - Download results as CSV
- ☁️ **Azure Ready** - Configured for Azure App Service deployment

---

## 🚀 Deploy to Azure

### Prerequisites

1. [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed
2. Azure subscription
3. Azure OpenAI resource with a deployed model

### Option 1: Quick Deploy Script

```bash
# Clone the repo
git clone <your-repo-url>
cd <repo-name>

# Run the deploy script
./deploy-azure.sh
```

The script will prompt you for:
- Azure OpenAI Endpoint
- Azure OpenAI API Key
- Azure OpenAI Deployment Name

### Option 2: Manual Azure CLI Deployment

```bash
# 1. Login to Azure
az login

# 2. Create resource group
az group create --name commission-calc-rg --location eastus

# 3. Create App Service plan
az appservice plan create \
    --name commission-calc-plan \
    --resource-group commission-calc-rg \
    --sku B1 \
    --is-linux

# 4. Create web app
az webapp create \
    --resource-group commission-calc-rg \
    --plan commission-calc-plan \
    --name your-app-name \
    --runtime "PYTHON:3.11"

# 5. Configure startup command
az webapp config set \
    --resource-group commission-calc-rg \
    --name your-app-name \
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout=600 --workers=2 app:app"

# 6. Set environment variables
az webapp config appsettings set \
    --resource-group commission-calc-rg \
    --name your-app-name \
    --settings \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_API_KEY="your-api-key" \
    AZURE_OPENAI_DEPLOYMENT="your-deployment-name" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview"

# 7. Deploy
az webapp up \
    --resource-group commission-calc-rg \
    --name your-app-name \
    --runtime "PYTHON:3.11"
```

### Option 3: GitHub Actions CI/CD

1. Push this repo to GitHub
2. In Azure Portal, download the **Publish Profile** from your App Service
3. Add GitHub secrets:
   - `AZURE_WEBAPP_NAME`: Your app service name
   - `AZURE_WEBAPP_PUBLISH_PROFILE`: Contents of the publish profile
4. Push to `main` branch to trigger deployment

---

## ⚙️ Azure OpenAI Setup

### 1. Create Azure OpenAI Resource

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "Azure OpenAI"
3. Create new resource
4. Wait for deployment to complete

### 2. Deploy a Model

1. Go to [Azure AI Foundry](https://ai.azure.com) or Azure OpenAI Studio
2. Select your resource
3. Go to **Deployments** → **Create new deployment**
4. Choose a model (recommended: `gpt-4o` or `gpt-4`)
5. Give it a deployment name (e.g., `gpt-4o-deploy`)

### 3. Get Your Credentials

From Azure Portal → Your OpenAI Resource → **Keys and Endpoint**:

| Setting | Where to Find |
|---------|---------------|
| `AZURE_OPENAI_ENDPOINT` | Endpoint URL |
| `AZURE_OPENAI_API_KEY` | KEY 1 or KEY 2 |
| `AZURE_OPENAI_DEPLOYMENT` | Your deployment name |

---

## 📊 How It Works

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
  Originator Pay = User Pay × Own Origination %
  ```
  ⚠️ **Critical:** Multiplies against User Pay, NOT total collected

### Output

```csv
matter,date,user,originator,total collected,user percentage,user pay,originator percentage,originator pay
Case-001,2024-01-15,John Smith,John Smith,10000.00,30.0%,3000.00,,
Case-002,2024-01-20,Jane Doe,John Smith,25000.00,25.0%,6250.00,10.0%,625.00
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | ✅ | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | ✅ | API key from Azure Portal |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | Your model deployment name |
| `AZURE_OPENAI_API_VERSION` | ❌ | Default: `2024-02-15-preview` |
| `SECRET_KEY` | ❌ | Flask secret key |

---

## 🏗️ Project Structure

```
.
├── app.py                      # Flask application
├── templates/
│   └── index.html              # Web interface
├── requirements.txt            # Python dependencies
├── startup.txt                 # Azure startup command
├── .deployment                 # Azure deployment config
├── deploy-azure.sh             # Deployment script
├── Dockerfile                  # Docker build (optional)
├── docker-compose.yml          # Docker Compose (optional)
├── .github/
│   └── workflows/
│       └── azure-deploy.yml    # GitHub Actions CI/CD
└── README.md
```

---

## 🔍 Monitoring & Logs

```bash
# View live logs
az webapp log tail --resource-group commission-calc-rg --name your-app-name

# View deployment logs
az webapp log deployment show --resource-group commission-calc-rg --name your-app-name

# Check app health
curl https://your-app-name.azurewebsites.net/health
```

---

## 💻 Local Development

```bash
# Create .env file
cp .env.example .env
# Edit .env with your Azure credentials

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

Open http://localhost:8000

---

## 📝 License

MIT

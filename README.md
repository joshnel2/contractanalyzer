# Attorney Commission Calculator

**No-code AI workflow** using n8n + Azure OpenAI to calculate attorney commissions.

## How It Works

1. **Upload Form** - Paste your CSV data
2. **Azure OpenAI** - AI calculates all commissions
3. **Download** - Get results as CSV

### Calculation Rules (AI Follows These)

| Agent | Rule |
|-------|------|
| **Agent 1 (User)** | `User Pay = Total Collected × User Percentage` |
| **Agent 2 (Originator)** | If different person: `Originator Pay = User Pay × Own Origination %` |
| **Same Person** | Originator fields left blank |

---

## 🚀 Deploy

### Step 1: Start n8n

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

docker-compose up -d
```

### Step 2: Open n8n

Go to **http://localhost:5678**

Login: `admin` / `changeme` (or what you set in .env)

### Step 3: Set Up Azure OpenAI Credentials

1. Click **Settings** (gear icon) → **Credentials**
2. Click **Add Credential** → Search **Azure OpenAI**
3. Fill in:
   - **API Key**: Your Azure OpenAI API key
   - **Endpoint**: `https://your-resource.openai.azure.com/`
   - **API Version**: `2024-02-15-preview`
4. Click **Save**

### Step 4: Import the Workflow

1. Go to **Workflows** → **Import from File**
2. Select `workflows/attorney-commission-calculator.json`
3. Open the **Azure OpenAI - Calculate** node
4. Select your Azure OpenAI credentials
5. Set the **Model** to your deployment name (e.g., `gpt-4o`)
6. **Save** the workflow

### Step 5: Activate & Use

1. Toggle **Active** (top-right) to ON
2. Click **Execute Workflow** or use the form URL
3. Paste your CSVs and submit!

---

## 📊 Input Format

### Case Data CSV
```
matter,date,total collected,user,originator
Case-001,2024-01-15,10000.00,John Smith,John Smith
Case-002,2024-01-20,25000.00,Jane Doe,John Smith
Case-003,2024-02-01,15000.00,Bob Johnson,Jane Doe
```

### Rules Sheet CSV
```
attorney name,user percentage,own origination other work percentage
John Smith,30%,10%
Jane Doe,25%,15%
Bob Johnson,35%,12%
```

---

## ☁️ Deploy to Azure

### Option 1: Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name n8n-commission-calc \
  --image n8nio/n8n \
  --ports 5678 \
  --environment-variables \
    N8N_BASIC_AUTH_ACTIVE=true \
    N8N_BASIC_AUTH_USER=admin \
    N8N_BASIC_AUTH_PASSWORD=your-password \
  --dns-name-label n8n-commission-calc
```

### Option 2: Azure App Service (Container)

1. Create a Container App Service
2. Use image: `n8nio/n8n`
3. Set environment variables from `.env.example`
4. Import the workflow after deployment

---

## 📁 Files

```
.
├── docker-compose.yml                      # Run n8n locally
├── .env.example                            # Configuration template
├── workflows/
│   └── attorney-commission-calculator.json # The AI workflow
└── README.md
```

---

## 🔧 Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Your API key |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (e.g., `gpt-4o`) |
| `N8N_USER` | n8n login username |
| `N8N_PASSWORD` | n8n login password |

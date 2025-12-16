# Attorney Commission Calculator

**No-code AI workflow** - n8n + Azure OpenAI

---

## 🚀 Deploy to Azure (One Command)

### Deploy n8n to Azure Container Instances:

```bash
az container create \
  --resource-group myResourceGroup \
  --name n8n-commissions \
  --image n8nio/n8n:latest \
  --ports 5678 \
  --cpu 1 \
  --memory 1.5 \
  --environment-variables \
    N8N_BASIC_AUTH_ACTIVE=true \
    N8N_BASIC_AUTH_USER=admin \
    N8N_BASIC_AUTH_PASSWORD=YourSecurePassword123 \
  --dns-name-label n8n-commissions \
  --location eastus
```

Your n8n will be live at: `http://n8n-commissions.eastus.azurecontainer.io:5678`

---

## 📥 Setup After Deployment

### 1. Login to n8n
Open your n8n URL and login with credentials you set above.

### 2. Add Azure OpenAI Credentials
1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **Azure OpenAI**
3. Enter:
   - **API Key**: Your key from Azure Portal
   - **Resource Name**: Your Azure OpenAI resource name
   - **API Version**: `2024-02-15-preview`
4. **Save**

### 3. Import the Workflow
1. Go to **Workflows** → **Import from File**
2. Upload `workflows/attorney-commission-calculator.json`
3. Click the **Azure OpenAI** node → select your credentials
4. Set **Model** to your deployment name (e.g., `gpt-4o`)
5. **Save**

### 4. Activate
Toggle **Active** to ON (top right)

### 5. Use It
Click the form URL or run manually - paste your CSVs and get results!

---

## 📊 Input/Output

**Case Data CSV:**
```
matter,date,total collected,user,originator
Case-001,2024-01-15,10000,John Smith,John Smith
Case-002,2024-01-20,25000,Jane Doe,John Smith
```

**Rules Sheet CSV:**
```
attorney name,user percentage,own origination other work percentage
John Smith,30%,10%
Jane Doe,25%,15%
```

**Output:** AI calculates and returns the commission CSV.

---

## Files

```
workflows/attorney-commission-calculator.json  ← Import this to n8n
```

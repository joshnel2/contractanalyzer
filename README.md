# Moltbot Azure AI Bridge

Connects Moltbot to Azure AI Foundry.

## Deploy to Azure Web App

1. **Delete** `moltazurebridge1` (it's set to Node.js, won't work)

2. **Create new Web App:**
   - Azure Portal → Create a resource → **Web App**
   - Runtime stack: **Python 3.11**
   - Operating System: **Linux**
   - Plan: Basic B1 or higher

3. **Connect GitHub:**
   - Go to new Web App → **Deployment Center**
   - Source: **GitHub**
   - Select this repo (`joshnel2/contractanalyzer`)
   - Branch: `main`
   - Save (Azure creates the workflow automatically)

4. **Add Environment Variables:**
   - Web App → **Configuration** → **Application settings**
   - Add:
     - `AZURE_OPENAI_KEY`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_DEPLOYMENT_NAME`

5. **Configure Moltbot:**
   - Set endpoint to: `https://YOUR-APP-NAME.azurewebsites.net`

## Endpoints

- `GET /` → `{"status": "Bridge Active"}`
- `POST /v1/chat/completions` → Main endpoint
- `POST /chat/completions` → Alternative

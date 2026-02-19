# Vela-Law

**AI-powered legal scheduling assistant built on [Microsoft Amplifier](https://github.com/microsoft/amplifier)**

> A secure, private, internal scheduling assistant for law firms. Attorneys simply
> CC an email to Vela, and she handles the rest — checking calendars, respecting
> preferences, proposing optimal times, and sending polished replies. When she's
> uncertain, she escalates with full context instead of guessing.

---

<!-- Screenshot placeholder — replace with actual screenshots after deployment -->
<!-- ![Vela-Law Dashboard](docs/screenshots/dashboard.png) -->
<!-- ![Vela Email Flow](docs/screenshots/email-flow.png) -->

## How It Works

```
Attorney CCs vela@ourfirm.onmicrosoft.com
         │
         ▼
┌─────────────────────┐
│   Azure Logic App   │  Watches shared mailbox, POSTs email JSON
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Azure Function App │  Runs Amplifier session with 14 custom tools
│   (function_app.py) │
└────────┬────────────┘
         │
    ┌────┴─────┐
    ▼          ▼
┌────────┐ ┌────────────┐
│ Graph  │ │ Table      │
│ API    │ │ Storage    │
│        │ │            │
│Calendar│ │Preferences │
│  Mail  │ │Audit Logs  │
│  Users │ │Thread State│
└────────┘ └────────────┘
```

1. **CC or forward** any scheduling email to `vela@ourfirm.onmicrosoft.com`
2. Vela **parses** the email for intent, participants, times, and urgency
3. **Loads** the requesting attorney's personal preferences (hours, buffers, tone, thresholds)
4. **Checks** Microsoft 365 calendars via Graph API
5. **Suggests** 2-3 optimal time slots with professional reasoning
6. **Sends** the reply automatically if confidence exceeds the attorney's threshold
7. **Escalates** with clear context when uncertain or when sensitive topics are detected
8. **Logs** every action with a full audit trail

Attorneys can update preferences by email:
```
Vela: set my buffer to 30 min
Vela: prefer 45-min internal calls
Vela: change my tone to friendly
Vela: block Dec 24-Jan 2 as blackout
```

---

## Architecture

### Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Harness | [Microsoft Amplifier](https://github.com/microsoft/amplifier) (agents, bundles, recipes) |
| LLM Provider | Azure OpenAI (GPT-4o or your deployment) |
| Calendar & Email | Microsoft Graph API (Calendar.ReadWrite, Mail.Send, User.Read.All) |
| Runtime | Azure Function App (Python 3.12, HTTP trigger) |
| Email Ingestion | Azure Logic App (Office 365 connector) |
| State & Preferences | Azure Table Storage |
| Auth | DefaultAzureCredential / Managed Identity |
| Dashboard | Streamlit (optional, for local preference management) |

### Amplifier Components

| Type | Name | Purpose |
|------|------|---------|
| **Agent** | `vela-law` | Core legal EA system prompt — warm, precise, ethical |
| **Bundle** | `vela-email-parsing` | Email intent extraction and attorney identification |
| **Bundle** | `vela-calendar-orchestration` | Calendar reads, slot finding, event creation |
| **Bundle** | `vela-preferences-manager` | Read/write/parse attorney preferences |
| **Bundle** | `vela-reply-drafting` | Tone-appropriate reply composition and sending |
| **Bundle** | `vela-escalation-handler` | Escalation evaluation and notification |
| **Recipe** | `new-scheduling-request` | Full end-to-end email processing flow |
| **Recipe** | `update-preferences` | Preference command processing flow |
| **Recipe** | `escalate-request` | Detailed escalation composition flow |

### Custom Tools (14 total)

| Tool | Bundle | Description |
|------|--------|-------------|
| `parse_email` | email_parsing | Extract structured scheduling intent from raw email |
| `identify_attorney` | email_parsing | Determine requesting attorney from addresses |
| `check_calendar` | calendar | Fetch events in a date range |
| `find_available_slots` | calendar | Find open slots respecting preferences & buffers |
| `create_calendar_event` | calendar | Book a meeting via Graph API |
| `check_multi_party_availability` | calendar | Find common free time across attendees |
| `get_preferences` | preferences | Load merged firm + attorney preferences |
| `update_preferences` | preferences | Apply preference changes |
| `parse_preference_command` | preferences | Interpret natural-language "Vela:" commands |
| `list_attorneys` | preferences | List all attorneys with stored prefs |
| `draft_reply` | reply | Compose tone-appropriate scheduling email |
| `send_reply` | reply | Send email from Vela shared mailbox |
| `evaluate_escalation` | escalation | Check if escalation is needed |
| `send_escalation` | escalation | Notify attorney of escalation |

---

## Project Structure

```
vela-law/
├── agents/
│   └── vela_law.md                  # Amplifier agent profile (system prompt)
├── behaviors/
│   └── vela_law.yaml                # Behavior bundle wiring
├── bundles/
│   ├── email_parsing.yaml           # Email parsing bundle manifest
│   ├── calendar_orchestration.yaml  # Calendar bundle manifest
│   ├── preferences_manager.yaml     # Preferences bundle manifest
│   ├── reply_drafting.yaml          # Reply drafting bundle manifest
│   └── escalation_handler.yaml      # Escalation bundle manifest
├── recipes/
│   ├── new_request.yaml             # Full scheduling flow
│   ├── update_prefs.yaml            # Preference update flow
│   └── escalate.yaml                # Escalation flow
├── tools/
│   ├── email_parser.py              # EmailParserTool, IdentifyAttorneyTool
│   ├── calendar_tools.py            # Calendar read/write/availability tools
│   ├── preferences_tools.py         # Preference CRUD + command parsing
│   ├── reply_tools.py               # DraftReplyTool, SendReplyTool
│   └── escalation_tools.py          # EvaluateEscalationTool, SendEscalationTool
├── core/
│   ├── config.py                    # Pydantic settings from environment
│   ├── models.py                    # Shared domain models
│   ├── graph_client.py              # Microsoft Graph API facade
│   ├── table_storage.py             # Azure Table Storage client
│   └── audit.py                     # Structured audit logger
├── dashboard/
│   └── app.py                       # Streamlit preferences UI
├── data/
│   ├── default_preferences.json     # Firm defaults + sample attorneys
│   └── seed_preferences.py          # Seed script for Table Storage
├── infrastructure/
│   ├── logic_app_template.json      # ARM template for Logic App
│   └── deploy.sh                    # One-command Azure deployment
├── .github/workflows/
│   └── deploy.yml                   # CI/CD pipeline
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── test_models.py               # Domain model tests
│   ├── test_email_parsing.py        # Email parser tool tests
│   ├── test_escalation.py           # Escalation logic tests
│   ├── test_calendar.py             # Calendar tool schema tests
│   └── test_preferences.py          # Preference tool tests
├── function_app.py                  # Azure Function entry point
├── host.json                        # Azure Functions host config
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata & tooling
├── .env.example                     # Environment variable template
└── README.md                        # This file
```

---

## Prerequisites

### Azure Resources

1. **Azure OpenAI** — Deploy a model (e.g. `gpt-4o`) and note:
   - Endpoint URL
   - API key
   - Deployment name

2. **Entra ID App Registration** — Create an app with these **Application** permissions:
   - `Calendars.ReadWrite`
   - `Mail.Send`
   - `User.Read.All`
   - Grant admin consent

3. **Shared Mailbox** — Create `vela@ourfirm.onmicrosoft.com` in Exchange admin

4. **Azure Storage Account** — For Table Storage (preferences, audit, threads)

5. **Azure Function App** — Python 3.12, Linux, Consumption plan

6. **Azure Logic App** — Office 365 connector watching the shared mailbox

### Local Development

- Python 3.12+
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) (`az login`)
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4
- [UV](https://docs.astral.sh/uv/) (optional, for fast installs)

---

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/vela-law.git
cd vela-law
cp .env.example .env
# Edit .env with your Azure details
```

### 2. Install Dependencies

```bash
# With pip
python -m pip install -r requirements.txt

# Or with uv (faster)
uv pip install -r requirements.txt
```

### 3. Seed Preferences

```bash
python data/seed_preferences.py
```

This loads firm-wide defaults and three sample attorney profiles into Table Storage.

### 4. Run Locally

```bash
# Start the Azure Function locally
func start

# The endpoint will be at http://localhost:7071/api/vela
```

### 5. Test with a Sample Email

```bash
curl -X POST http://localhost:7071/api/vela \
  -H "Content-Type: application/json" \
  -d '{
    "Id": "test-001",
    "From": "jsmith@externalclient.com",
    "To": "j.nakamura@ourfirm.onmicrosoft.com;vela@ourfirm.onmicrosoft.com",
    "Subject": "Meeting Request: Q1 Strategy Review",
    "Body": "Hi Jun, could we schedule a 60-minute meeting next week? Tuesday or Wednesday afternoon works best.",
    "DateTimeReceived": "2026-02-19T14:30:00Z"
  }'
```

### 6. Launch the Dashboard (Optional)

```bash
pip install streamlit
streamlit run dashboard/app.py
```

---

## Deploy to Azure

### Option A: One-Command Deploy

```bash
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

### Option B: Step-by-Step

```bash
# 1. Create resource group
az group create --name vela-law-rg --location eastus

# 2. Create storage account
az storage account create \
  --name velalawstorage \
  --resource-group vela-law-rg \
  --sku Standard_LRS

# 3. Create Function App
az functionapp create \
  --name vela-law-func \
  --resource-group vela-law-rg \
  --storage-account velalawstorage \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --os-type Linux

# 4. Configure settings
az functionapp config appsettings set \
  --name vela-law-func \
  --resource-group vela-law-rg \
  --settings \
    AZURE_OPENAI_API_KEY="your-key" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_STORAGE_CONNECTION_STRING="your-connection-string" \
    VELA_MAILBOX="vela@ourfirm.onmicrosoft.com"

# 5. Enable Managed Identity
az functionapp identity assign \
  --name vela-law-func \
  --resource-group vela-law-rg

# 6. Deploy code
func azure functionapp publish vela-law-func --python

# 7. Deploy Logic App
az deployment group create \
  --resource-group vela-law-rg \
  --template-file infrastructure/logic_app_template.json \
  --parameters \
    velaFunctionUrl="https://vela-law-func.azurewebsites.net/api/vela" \
    velaFunctionKey="your-function-key"
```

### Option C: GitHub Actions (CI/CD)

The included `.github/workflows/deploy.yml` runs lint, tests, and deploys on push to `main`. Configure these GitHub secrets:

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Entra app registration client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |

---

## Customization

### Adding a New Tool

1. Create a new Python class in `tools/` implementing the Amplifier Tool protocol:

```python
from amplifier_core import ToolResult

class MyCustomTool:
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "What this tool does"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": { ... },
            "required": [ ... ],
        }

    async def execute(self, input: dict) -> ToolResult:
        # Your logic here
        return ToolResult(success=True, output="result")
```

2. Mount it in `function_app.py`:

```python
await coordinator.mount("tools", MyCustomTool(), name="my_tool")
```

3. Add it to the agent profile in `agents/vela_law.md` (tools table).

### Adding a New Recipe

Create a YAML file in `recipes/` following the Amplifier recipe schema. Recipes are multi-step agent workflows — see `recipes/new_request.yaml` for the pattern.

### Customizing Attorney Preferences

Edit `data/default_preferences.json` for firm-wide defaults, or use:
- The Streamlit dashboard (`streamlit run dashboard/app.py`)
- Email commands (`Vela: set my buffer to 30 min`)
- Direct Table Storage edits via Azure Portal

### Available Preference Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `working_hours_start` | string | `"08:00"` | Day start time |
| `working_hours_end` | string | `"18:00"` | Day end time |
| `timezone` | string | `"America/New_York"` | IANA timezone |
| `buffer_before_minutes` | int | `15` | Buffer before meetings |
| `buffer_after_minutes` | int | `10` | Buffer after meetings |
| `preferred_duration_internal` | int | `30` | Internal meeting length (min) |
| `preferred_duration_client` | int | `60` | Client meeting length (min) |
| `response_tone` | string | `"formal"` | `formal`, `friendly`, or `concise` |
| `auto_approve_threshold` | int | `85` | Confidence % for auto-send |
| `blackout_dates` | list | `[]` | ISO dates to block |
| `blocked_times` | list | `[]` | Recurring blocks, e.g. `"MWF 12:00-13:00"` |
| `favorite_locations` | list | `[]` | Preferred meeting rooms |
| `default_virtual_platform` | string | `"Microsoft Teams"` | Default video platform |
| `escalation_keywords` | list | `[...]` | Triggers automatic escalation |
| `custom_signature` | string | `""` | Email signature for replies |

---

## Security & Compliance

- **Tenant isolation** — All data stays within your Azure tenant. No external API calls except to Azure OpenAI and Microsoft Graph (both within your tenant).
- **Managed Identity** — No secrets in code for Graph API calls in production.
- **Full audit trail** — Every email received, every decision made, every reply sent is logged to Azure Table Storage with timestamps.
- **Escalation by default** — Vela never guesses on sensitive matters. Rate discussions, conflicts of interest, travel, and multi-party negotiations always escalate.
- **Conservative prompts** — The system prompt explicitly forbids disclosing client information, fabricating details, or overriding attorney preferences.
- **Configurable thresholds** — Each attorney controls their own auto-approve confidence threshold.

---

## Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ -v --cov=core --cov=tools --cov-report=term-missing
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `AZURE_OPENAI_API_KEY not set` | Copy `.env.example` to `.env` and fill in values |
| `Table Storage connection error` | Verify `AZURE_STORAGE_CONNECTION_STRING` or use Azurite for local dev |
| `Graph API 403 Forbidden` | Ensure Managed Identity has `Calendars.ReadWrite`, `Mail.Send`, `User.Read.All` |
| `Logic App not triggering` | Check the Office 365 connection is authenticated and the shared mailbox exists |
| `Function timeout` | Increase `functionTimeout` in `host.json` (default: 5 min) |
| `Module not found: amplifier_core` | Run `pip install -r requirements.txt` to install Amplifier |
| Dashboard won't load | Install Streamlit: `pip install streamlit` |

---

## License

Internal use only. Modify and distribute within your firm as needed.

---

Built with [Microsoft Amplifier](https://github.com/microsoft/amplifier) by your LegalTech team.

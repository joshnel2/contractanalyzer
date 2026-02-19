# Strapped AI

**AI-powered scheduling assistant built on [Microsoft Amplifier](https://github.com/microsoft/amplifier)**

> Stop playing calendar tetris. Just CC an email and Strapped handles
> calendars, preferences, time zones, and follow-ups — so you can focus on
> what actually matters.

---

## How It Works

```
Team member CCs strapped@yourcompany.com
         │
         ▼
┌─────────────────────┐
│   Azure Logic App   │  Watches shared mailbox, POSTs email JSON
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Azure Function App │  Runs Amplifier session with 14 custom tools
│  (function_app.py)  │
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

1. **CC or forward** any scheduling email to `strapped@yourcompany.com`
2. Strapped **parses** the email for intent, participants, times, and urgency
3. **Loads** the person's preferences (hours, buffers, tone, thresholds)
4. **Checks** Microsoft 365 calendars via Graph API
5. **Suggests** 2-3 optimal time slots with professional reasoning
6. **Sends** the reply automatically if confidence exceeds the threshold
7. **Escalates** with clear context when uncertain or sensitive topics detected
8. **Logs** every action with a full audit trail

Update preferences by email — no dashboard needed:
```
Strapped: set my buffer to 30 min
Strapped: prefer 45-min internal calls
Strapped: change my tone to friendly
```

---

## Web App

Strapped AI includes a full web application:

| Route | Description |
|-------|-------------|
| `/` | Landing page — features, how it works, call to action |
| `/book-demo` | Demo booking form for prospects |
| `/login` | Login for existing customers |
| `/signup` | Account registration |
| `/dashboard` | Preferences editor and activity log (protected) |

Run locally:
```bash
pip install -r requirements.txt
uvicorn web.app:app --reload --port 8000
```

---

## Architecture

### Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Harness | [Microsoft Amplifier](https://github.com/microsoft/amplifier) |
| LLM Provider | Azure OpenAI |
| Calendar & Email | Microsoft Graph API |
| Runtime | Azure Function App (Python 3.12) |
| Email Ingestion | Azure Logic App |
| State & Preferences | Azure Table Storage |
| Auth | JWT sessions + bcrypt passwords |
| Web App | FastAPI + Jinja2 + Tailwind CSS |

---

## Project Structure

```
strapped-ai/
├── agents/
│   └── strapped_ai.md              # Agent system prompt
├── behaviors/
│   └── strapped_ai.yaml            # Behavior bundle
├── bundles/                         # 5 tool bundle manifests
├── recipes/                         # 3 workflow recipes
├── tools/                           # 14 custom Amplifier tools
│   ├── email_parser.py
│   ├── calendar_tools.py
│   ├── preferences_tools.py
│   ├── reply_tools.py
│   └── escalation_tools.py
├── core/                            # Infrastructure
│   ├── config.py
│   ├── models.py
│   ├── graph_client.py
│   ├── table_storage.py
│   └── audit.py
├── web/                             # Web application
│   ├── app.py                       # FastAPI app
│   ├── auth.py                      # JWT auth + user store
│   └── templates/
│       ├── base.html
│       ├── landing.html
│       ├── login.html
│       ├── signup.html
│       ├── book_demo.html
│       └── dashboard.html
├── data/                            # Default prefs + seed script
├── infrastructure/                  # Deploy script + Logic App ARM
├── .github/workflows/deploy.yml     # CI/CD
├── tests/                           # Test suite
├── function_app.py                  # Azure Function entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd strapped-ai
cp .env.example .env
# Fill in your Azure details in .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Seed Sample Data

```bash
python data/seed_preferences.py
```

### 4. Run the Web App

```bash
uvicorn web.app:app --reload --port 8000
# Open http://localhost:8000
```

### 5. Run the Function App

```bash
func start
# Endpoint: http://localhost:7071/api/strapped
```

### 6. Test with a Sample Email

```bash
curl -X POST http://localhost:7071/api/strapped \
  -H "Content-Type: application/json" \
  -d '{
    "Id": "test-001",
    "From": "client@external.com",
    "To": "j.nakamura@yourcompany.com;strapped@yourcompany.com",
    "Subject": "Meeting Request: Q1 Strategy Review",
    "Body": "Can we schedule a 60-minute meeting next week?",
    "DateTimeReceived": "2026-02-19T14:30:00Z"
  }'
```

---

## Prerequisites

### Azure Resources

1. **Azure OpenAI** — Deploy a model and note the endpoint, key, and deployment name
2. **Entra ID App Registration** — `Calendars.ReadWrite`, `Mail.Send`, `User.Read.All`
3. **Shared Mailbox** — Create `strapped@yourcompany.com` in Exchange admin
4. **Azure Storage Account** — For Table Storage
5. **Azure Function App** — Python 3.12, Linux

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
VELA_MAILBOX=strapped@yourcompany.com
```

---

## Deploy to Azure

```bash
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

Or use the included GitHub Actions workflow (`.github/workflows/deploy.yml`).

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT

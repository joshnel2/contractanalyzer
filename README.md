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
┌─────────────────────┐       ┌────────────────┐
│  Azure Function App │──────▶│   PostgreSQL    │
│  (email processing) │       │                │
└─────────────────────┘       │  preferences   │
                              │  audit log     │
┌─────────────────────┐       │  users         │
│   Azure Web App     │──────▶│  threads       │
│  (landing + dash)   │       │  demo requests │
└─────────────────────┘       └────────────────┘
         │
         ▼
    Microsoft Graph API
    (Calendar · Mail · Users)
```

1. **CC or forward** any scheduling email to `strapped@yourcompany.com`
2. Strapped **parses** the email for intent, participants, times, and urgency
3. **Loads** the person's preferences (hours, buffers, tone, thresholds)
4. **Checks** Microsoft 365 calendars via Graph API
5. **Suggests** 2-3 optimal time slots with professional reasoning
6. **Sends** the reply automatically if confidence exceeds the threshold
7. **Escalates** with clear context when uncertain

Update preferences by email — no dashboard needed:
```
Strapped: set my buffer to 30 min
Strapped: prefer 45-min internal calls
Strapped: change my tone to friendly
```

---

## Web App

| Route | Description |
|-------|-------------|
| `/` | Landing page — features, how it works, book a demo |
| `/book-demo` | Demo booking form for prospects |
| `/login` | Login for existing customers |
| `/signup` | Account registration |
| `/dashboard` | Preferences editor and activity log (protected) |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Harness | [Microsoft Amplifier](https://github.com/microsoft/amplifier) |
| LLM | Azure OpenAI |
| Database | **PostgreSQL** (Azure Database for PostgreSQL) |
| Calendar & Email | Microsoft Graph API |
| Email Processing | Azure Function App (Python 3.12) |
| Web Frontend | Azure Web App + FastAPI + Jinja2 + Tailwind CSS |
| Auth | JWT sessions + bcrypt passwords |

---

## Project Structure

```
strapped-ai/
├── agents/strapped_ai.md           # Agent system prompt
├── bundles/                         # 5 tool bundle manifests
├── recipes/                         # 3 workflow recipes
├── tools/                           # 14 custom Amplifier tools
├── core/
│   ├── config.py                    # Environment-based settings
│   ├── database.py                  # SQLAlchemy engine + session
│   ├── db_models.py                 # PostgreSQL ORM models
│   ├── table_storage.py             # Storage facade (PostgreSQL)
│   ├── models.py                    # Pydantic domain models
│   ├── graph_client.py              # MS Graph API client
│   └── audit.py                     # Audit logger
├── web/
│   ├── app.py                       # FastAPI application
│   ├── auth.py                      # JWT auth + user store
│   └── templates/                   # Jinja2 + Tailwind templates
├── data/
│   ├── default_preferences.json     # Sample preferences
│   └── seed_preferences.py          # DB seed script
├── infrastructure/
│   ├── deploy.sh                    # Full Azure deployment
│   └── logic_app_template.json      # Email trigger ARM template
├── function_app.py                  # Azure Function (email processing)
├── startup.sh                       # Azure Web App startup command
├── requirements.txt
├── .env.example
└── tests/
```

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL running locally (or use Docker below)

```bash
# Start PostgreSQL with Docker
docker run -d --name strapped-pg \
  -e POSTGRES_USER=strapped \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=strapped \
  -p 5432:5432 postgres:16
```

### 2. Clone and Configure

```bash
git clone <your-repo-url>
cd strapped-ai
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialise the Database

```bash
python -m core.database
```

### 5. Seed Sample Data

```bash
python data/seed_preferences.py
```

### 6. Run the Web App

```bash
uvicorn web.app:app --reload --port 8000
# Open http://localhost:8000
```

### 7. Run the Function App (optional)

```bash
func start
# Endpoint: http://localhost:7071/api/strapped
```

---

## Deploy to Azure

### One-Command Deploy

Creates PostgreSQL, Web App, and Function App:

```bash
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

### What Gets Created

| Resource | Purpose |
|----------|---------|
| Azure Database for PostgreSQL | All data storage |
| Azure Web App | Landing page, auth, dashboard |
| Azure Function App | Email processing pipeline |
| App Service Plan | Shared hosting for both apps |

### CI/CD

The `.github/workflows/deploy.yml` pipeline runs tests against a PostgreSQL service container, then deploys both the Web App and Function App.

GitHub secrets needed:

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Entra app registration |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_SUBSCRIPTION_ID` | Subscription |

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Web app authentication |
| `preferences` | Per-person scheduling preferences |
| `firm_defaults` | Firm-wide default values |
| `audit_log` | Every action Strapped takes |
| `threads` | Conversation thread state |
| `demo_requests` | Demo booking submissions |

Tables are auto-created on startup via SQLAlchemy `create_all()`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AZURE_OPENAI_API_KEY` | For assistant | Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | For assistant | Model deployment name |
| `AZURE_OPENAI_ENDPOINT` | For assistant | OpenAI resource URL |
| `AZURE_TENANT_ID` | For Graph API | Entra ID tenant |
| `AZURE_CLIENT_ID` | For Graph API | App registration |
| `AZURE_CLIENT_SECRET` | For Graph API | App secret |
| `VELA_MAILBOX` | For assistant | Shared mailbox address |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT

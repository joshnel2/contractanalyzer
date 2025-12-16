# Attorney Commission Calculator - n8n Workflow

This n8n workflow calculates attorney commissions from case data and rules sheets.

## Calculation Logic

### Agent 1: User Calculation
1. Find the `user` from Case Data in the Rules Sheet
2. Calculate: **User Pay = Total Collected × User Percentage**

### Agent 2: Originator Calculation
1. Compare `originator` with `user`
2. **If SAME person:** Leave Originator fields blank
3. **If DIFFERENT:** Calculate: **Originator Pay = User Pay × Own Origination Other Work Percentage**
   - ⚠️ Multiplies against User Pay, NOT total collected

## Quick Start

### 1. Start n8n

```bash
cp .env.example .env
docker-compose up -d
```

Access n8n at: **http://localhost:5678** (admin / changeme)

### 2. Import the Workflow

1. Open n8n → **Workflows** → **Import from File**
2. Select `workflows/attorney-commission-calculator.json`
3. **Activate** the workflow (toggle in top-right)

### 3. Use the Workflow

**Via API (JSON body):**

```bash
curl -X POST http://localhost:5678/webhook/calculate-commissions \
  -H "Content-Type: application/json" \
  -d '{
    "case_data_csv": "matter,date,total collected,user,originator\nCase-001,2024-01-15,10000.00,John Smith,John Smith\nCase-002,2024-01-20,25000.00,Jane Doe,John Smith",
    "rules_sheet_csv": "attorney name,user percentage,own origination other work percentage\nJohn Smith,30%,10%\nJane Doe,25%,15%"
  }'
```

**Using the test script:**

```bash
./test-workflow.sh
```

## Input Format

### Case Data CSV
```csv
matter,date,total collected,user,originator
Case-001,2024-01-15,10000.00,John Smith,John Smith
Case-002,2024-01-20,25000.00,Jane Doe,John Smith
```

### Rules Sheet CSV
```csv
attorney name,user percentage,own origination other work percentage
John Smith,30%,10%
Jane Doe,25%,15%
```

## Output Format

```csv
matter,date,user,originator,total collected,user percentage,user pay,originator percentage,originator pay
Case-001,2024-01-15,John Smith,John Smith,10000.00,30.0%,3000.00,,
Case-002,2024-01-20,Jane Doe,John Smith,25000.00,25.0%,6250.00,10.0%,625.00
```

Note: When user = originator, originator percentage and pay are left blank.

## File Structure

```
.
├── docker-compose.yml              # n8n Docker config
├── .env.example                    # Environment template
├── README.md
├── test-workflow.sh                # Test script
├── workflows/
│   └── attorney-commission-calculator.json
└── sample-data/
    ├── case_data.csv
    └── rules_sheet.csv
```

## Deployment

### Local Development
```bash
docker-compose up -d
```

### Production
1. Set secure passwords in `.env`
2. Configure reverse proxy with SSL
3. Update `N8N_HOST` and `WEBHOOK_URL` to your domain

### Cloud (Railway, Render, Fly.io)
Push this repo and set environment variables in their dashboard.

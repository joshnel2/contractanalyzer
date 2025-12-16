# n8n Workflow Deployment

This repository contains an n8n workflow automation setup ready for deployment.

## Quick Start

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed

### 2. Setup

```bash
# Clone this repository
git clone <your-repo-url>
cd <repo-name>

# Copy environment file and configure
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 3. Run Locally

```bash
# Start n8n
docker-compose up -d

# View logs
docker-compose logs -f
```

Access n8n at: **http://localhost:5678**

Default credentials (change in `.env`):
- Username: `admin`
- Password: `changeme`

### 4. Import Workflows

1. Open n8n in your browser
2. Go to **Workflows** → **Import from File**
3. Select workflows from the `./workflows` directory

## Production Deployment

### Deploy to a Server

1. **Set up a server** (DigitalOcean, AWS, etc.) with Docker installed

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit with production values:
   # - N8N_HOST=your-domain.com
   # - N8N_PROTOCOL=https
   # - Strong passwords
   ```

3. **Add reverse proxy (nginx example):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:5678;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **Start n8n:**
   ```bash
   docker-compose up -d
   ```

### Deploy to Railway/Render/Fly.io

These platforms support Docker deployments. Push this repo and configure environment variables in their dashboards.

## Workflows

Store your workflow JSON exports in the `./workflows` directory for version control.

### Export a Workflow

1. In n8n, open the workflow
2. Click **...** → **Download**
3. Save to `./workflows/`

### Sample Workflow

A sample webhook workflow is included at `./workflows/sample-webhook-workflow.json`

## Directory Structure

```
.
├── docker-compose.yml    # n8n Docker configuration
├── .env.example          # Environment variables template
├── .gitignore
├── README.md
└── workflows/            # Workflow JSON files (version controlled)
    └── sample-webhook-workflow.json
```

## Useful Commands

```bash
# Start n8n
docker-compose up -d

# Stop n8n
docker-compose down

# View logs
docker-compose logs -f n8n

# Restart n8n
docker-compose restart

# Update n8n to latest version
docker-compose pull
docker-compose up -d
```

## Resources

- [n8n Documentation](https://docs.n8n.io/)
- [n8n Community](https://community.n8n.io/)
- [Workflow Templates](https://n8n.io/workflows)

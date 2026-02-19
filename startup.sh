#!/usr/bin/env bash
# Azure Web App startup command.
# Initialises the database then starts the Gunicorn server.

python -m core.database
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker web.app:app --bind 0.0.0.0:8000 --timeout 120

"""Strapped AI Azure Function App — digest generation endpoint.

Provides two HTTP triggers:
  POST /api/strapped/digest   — generate and send a digest for a user
  GET  /api/strapped/health   — health check

The web app or a timer trigger calls the digest endpoint to generate
email + calendar summaries and notify the user.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import azure.functions as func
from dotenv import load_dotenv

load_dotenv()

from core.config import settings
from core.audit import AuditLogger
from core.database import init_db
from core.graph_client import StrappedGraphClient
from core.table_storage import StrappedTableStorage

from tools.email_tools import ReadEmailsTool
from tools.calendar_tools import ReadCalendarTool
from tools.notification_tools import SendDigestTool
from tools.preferences_tools import GetPreferencesTool, UpdatePreferencesTool

logging.basicConfig(
    level=getattr(logging, settings.strapped_log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("strapped.function")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="strapped/digest", methods=["POST"])
async def digest_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Generate and send an email + calendar digest for a user."""
    logger.info("Digest endpoint invoked")

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON — provide {\"user_email\": \"...\"}"}),
            status_code=400,
            mimetype="application/json",
        )

    user_email = body.get("user_email", "")
    if not user_email:
        return func.HttpResponse(
            json.dumps({"error": "user_email is required"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        result = await _generate_digest(user_email)
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception:
        logger.exception("Digest generation failed for %s", user_email)
        return func.HttpResponse(
            json.dumps({"error": "Digest generation failed", "trace": traceback.format_exc()}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="strapped/health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}),
        status_code=200,
        mimetype="application/json",
    )


async def _generate_digest(user_email: str) -> dict[str, Any]:
    """Read emails + calendar, run the Amplifier session, send the digest."""

    init_db()
    storage = StrappedTableStorage()
    graph = StrappedGraphClient()
    audit = AuditLogger(storage)

    audit.log(user_email, "digest_requested")

    session = await _build_session(storage, graph)

    prompt = f"""\
Generate a daily digest for {user_email}.

1. Use `read_emails` to fetch their recent emails (last 24 hours).
2. Use `read_calendar` to fetch their upcoming events (next 3 days).
3. Summarise everything following your digest format:
   - Email summary (urgent / FYI / low priority)
   - Calendar summary (today / tomorrow / this week)
   - Action items
4. Use `send_digest` to email the summary to {user_email}.

The Strapped shared mailbox is: {settings.strapped_mailbox}
"""

    try:
        async with session:
            response = await session.execute(prompt)
    except Exception:
        logger.exception("Amplifier session failed")
        audit.log(user_email, "digest_error", outcome="error")
        raise

    audit.log(user_email, "digest_sent", outcome="sent")

    return {
        "status": "digest_sent",
        "user_email": user_email,
        "response_preview": response[:500],
    }


async def _build_session(
    storage: StrappedTableStorage,
    graph: StrappedGraphClient,
) -> Any:
    """Build an Amplifier session with the digest tools."""
    from amplifier_core import AmplifierSession
    from amplifier_foundation import Bundle, load_bundle

    foundation_source = "git+https://github.com/microsoft/amplifier-foundation@main"
    foundation = await load_bundle(foundation_source)

    provider_bundle = Bundle(
        name="provider-azure-openai",
        version="1.0.0",
        providers=[{
            "module": "provider-openai",
            "source": "git+https://github.com/microsoft/amplifier-module-provider-openai@main",
            "config": {
                "api_type": "azure",
                "azure_endpoint": settings.azure_openai_endpoint,
                "api_key": settings.azure_openai_api_key,
                "default_model": settings.azure_openai_deployment_name,
                "api_version": "2024-12-01-preview",
            },
        }],
    )

    agent_md = Path(__file__).parent / "agents" / "strapped_ai.md"
    agent_instruction = ""
    if agent_md.exists():
        raw = agent_md.read_text()
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            agent_instruction = parts[2].strip() if len(parts) > 2 else raw
        else:
            agent_instruction = raw

    app_bundle = Bundle(
        name="strapped-ai",
        version="1.0.0",
        instruction=agent_instruction,
        session={
            "orchestrator": {
                "module": "loop-basic",
                "source": "git+https://github.com/microsoft/amplifier-module-loop-basic@main",
                "config": {"max_iterations": 10},
            },
            "context": {
                "module": "context-simple",
                "source": "git+https://github.com/microsoft/amplifier-module-context-simple@main",
                "config": {"max_tokens": 128000},
            },
        },
    )

    composed = foundation.compose(provider_bundle).compose(app_bundle)
    prepared = await composed.prepare()
    session = await prepared.create_session(session_cwd=Path.cwd())

    coordinator = session.coordinator
    await coordinator.mount("tools", ReadEmailsTool(graph), name="read_emails")
    await coordinator.mount("tools", ReadCalendarTool(graph), name="read_calendar")
    await coordinator.mount("tools", SendDigestTool(graph, settings.strapped_mailbox), name="send_digest")
    await coordinator.mount("tools", GetPreferencesTool(storage), name="get_preferences")
    await coordinator.mount("tools", UpdatePreferencesTool(storage), name="update_preferences")

    logger.info("Amplifier session built with 5 tools")
    return session

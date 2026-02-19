"""Vela-Law Azure Function App — HTTP trigger entry point.

This is the production runtime. A Logic App watches the Vela shared mailbox
and POSTs each inbound email as JSON to the ``/api/vela`` endpoint. The
function spins up an Amplifier session with all Vela tools mounted, processes
the email, and either auto-replies or escalates.

Architecture
────────────
  Logic App  →  POST /api/vela  →  Amplifier Session  →  Graph API
                                        │
                                   Azure Table Storage
                                  (prefs, audit, threads)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import azure.functions as func
from dotenv import load_dotenv

load_dotenv()

from core.config import settings
from core.audit import AuditLogger
from core.graph_client import VelaGraphClient
from core.models import InboundEmail, EmailIntent
from core.table_storage import VelaTableStorage

from tools.email_parser import EmailParserTool, IdentifyAttorneyTool
from tools.calendar_tools import (
    CheckCalendarTool,
    CheckMultiPartyAvailabilityTool,
    CreateCalendarEventTool,
    FindAvailableSlotsTool,
)
from tools.preferences_tools import (
    GetPreferencesTool,
    ListAttorneysTool,
    ParsePreferenceCommandTool,
    UpdatePreferencesTool,
)
from tools.reply_tools import DraftReplyTool, SendReplyTool
from tools.escalation_tools import EvaluateEscalationTool, SendEscalationTool

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.vela_log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("vela.function")

# ── Azure Function App ───────────────────────────────────────────────────────

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="vela", methods=["POST"])
async def vela_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Main entry point — receives email JSON from Logic App."""
    logger.info("Vela endpoint invoked")

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON payload"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        result = await _process_email(body)
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception:
        logger.exception("Unhandled error in vela_endpoint")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal processing error",
                "trace": traceback.format_exc(),
            }),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="vela/health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Lightweight health probe for monitoring."""
    return func.HttpResponse(
        json.dumps({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}),
        status_code=200,
        mimetype="application/json",
    )


# ── Core Processing Pipeline ────────────────────────────────────────────────


async def _process_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Orchestrate the full Vela-Law pipeline for one inbound email."""

    # 1. Normalise the inbound email
    email = _normalise_email(payload)
    logger.info("Processing email: %s (from %s)", email.subject, email.from_address)

    # 2. Initialise infrastructure
    storage = VelaTableStorage(settings.azure_storage_connection_string)
    graph = VelaGraphClient()
    audit = AuditLogger(storage)

    audit.email_received(email.from_address, email.message_id, email.subject)

    # 3. Build the Amplifier session with all tools
    session, agent_instruction = await _build_session(storage, graph)

    # 4. Compose the master prompt with the email context
    master_prompt = _build_master_prompt(email)

    # 5. Execute the Amplifier session
    try:
        async with session:
            response = await session.execute(master_prompt)
    except Exception:
        logger.exception("Amplifier session failed")
        audit.log(
            email.from_address,
            "session_error",
            message_id=email.message_id,
            outcome="error",
        )
        raise

    # 6. Save thread state
    storage.save_thread(
        email.conversation_id or email.message_id,
        {
            "last_email_id": email.message_id,
            "last_response": response[:2000],
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "status": "processed",
        "message_id": email.message_id,
        "response_preview": response[:500],
    }


async def _build_session(
    storage: VelaTableStorage,
    graph: VelaGraphClient,
) -> tuple[Any, str]:
    """Construct and return a fully-armed Amplifier session.

    Loads the foundation bundle, composes with Azure OpenAI provider,
    and mounts all Vela custom tools.
    """
    from amplifier_core import AmplifierSession
    from amplifier_foundation import Bundle, load_bundle

    # Load the Amplifier foundation from GitHub
    foundation_source = "git+https://github.com/microsoft/amplifier-foundation@main"
    foundation = await load_bundle(foundation_source)

    # Configure the Azure OpenAI provider
    provider_bundle = Bundle(
        name="provider-azure-openai",
        version="1.0.0",
        providers=[
            {
                "module": "provider-openai",
                "source": "git+https://github.com/microsoft/amplifier-module-provider-openai@main",
                "config": {
                    "api_type": "azure",
                    "azure_endpoint": settings.azure_openai_endpoint,
                    "api_key": settings.azure_openai_api_key,
                    "default_model": settings.azure_openai_deployment_name,
                    "api_version": "2024-12-01-preview",
                },
            },
        ],
    )

    # Load the Vela-Law agent instruction from the agent markdown file
    agent_md = Path(__file__).parent / "agents" / "vela_law.md"
    agent_instruction = ""
    if agent_md.exists():
        raw = agent_md.read_text()
        # Strip frontmatter
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            agent_instruction = parts[2].strip() if len(parts) > 2 else raw
        else:
            agent_instruction = raw

    # Compose the Vela bundle with instruction
    vela_bundle = Bundle(
        name="vela-law",
        version="1.0.0",
        instruction=agent_instruction,
        session={
            "orchestrator": {
                "module": "loop-basic",
                "source": "git+https://github.com/microsoft/amplifier-module-loop-basic@main",
                "config": {"max_iterations": 20},
            },
            "context": {
                "module": "context-simple",
                "source": "git+https://github.com/microsoft/amplifier-module-context-simple@main",
                "config": {"max_tokens": 128000},
            },
        },
    )

    composed = foundation.compose(provider_bundle).compose(vela_bundle)

    # Prepare and create session
    prepared = await composed.prepare()
    session = await prepared.create_session(session_cwd=Path.cwd())

    # Mount all custom Vela tools
    coordinator = session.coordinator

    # Email parsing tools
    await coordinator.mount("tools", EmailParserTool(), name="parse_email")
    await coordinator.mount("tools", IdentifyAttorneyTool(), name="identify_attorney")

    # Calendar tools
    await coordinator.mount("tools", CheckCalendarTool(graph), name="check_calendar")
    await coordinator.mount("tools", FindAvailableSlotsTool(graph), name="find_available_slots")
    await coordinator.mount("tools", CreateCalendarEventTool(graph), name="create_calendar_event")
    await coordinator.mount(
        "tools",
        CheckMultiPartyAvailabilityTool(graph),
        name="check_multi_party_availability",
    )

    # Preference tools
    await coordinator.mount("tools", GetPreferencesTool(storage), name="get_preferences")
    await coordinator.mount("tools", UpdatePreferencesTool(storage), name="update_preferences")
    await coordinator.mount("tools", ParsePreferenceCommandTool(), name="parse_preference_command")
    await coordinator.mount("tools", ListAttorneysTool(storage), name="list_attorneys")

    # Reply tools
    await coordinator.mount("tools", DraftReplyTool(), name="draft_reply")
    await coordinator.mount(
        "tools",
        SendReplyTool(graph, settings.vela_mailbox),
        name="send_reply",
    )

    # Escalation tools
    await coordinator.mount("tools", EvaluateEscalationTool(), name="evaluate_escalation")
    await coordinator.mount(
        "tools",
        SendEscalationTool(graph, settings.vela_mailbox),
        name="send_escalation",
    )

    logger.info("Amplifier session built with %d custom tools", 14)
    return session, agent_instruction


# ── Helpers ──────────────────────────────────────────────────────────────────


def _normalise_email(payload: dict[str, Any]) -> InboundEmail:
    """Map the Logic App JSON payload to our InboundEmail model.

    The Logic App connector for Office 365 produces keys like:
        From, To, Cc, Subject, Body, DateTimeReceived, Id, ConversationId, etc.
    We normalise these into our Pydantic model.
    """
    return InboundEmail(
        message_id=payload.get("Id") or payload.get("message_id") or "",
        conversation_id=payload.get("ConversationId") or payload.get("conversation_id") or "",
        from_address=(
            payload.get("From", "")
            if isinstance(payload.get("From"), str)
            else payload.get("From", {}).get("Address", payload.get("from_address", ""))
        ),
        from_name=payload.get("FromName") or payload.get("from_name") or "",
        to_addresses=_extract_addresses(payload.get("To") or payload.get("to_addresses") or []),
        cc_addresses=_extract_addresses(payload.get("Cc") or payload.get("cc_addresses") or []),
        subject=payload.get("Subject") or payload.get("subject") or "",
        body_text=payload.get("BodyPreview") or payload.get("Body") or payload.get("body_text") or "",
        body_html=payload.get("Body") or payload.get("body_html") or "",
        received_at=datetime.fromisoformat(
            payload.get("DateTimeReceived")
            or payload.get("received_at")
            or datetime.now(timezone.utc).isoformat()
        ),
        has_attachments=payload.get("HasAttachments", False),
        importance=payload.get("Importance", "normal"),
    )


def _extract_addresses(raw: Any) -> list[str]:
    """Flexibly extract email addresses from various Logic App formats."""
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(item.get("Address") or item.get("address") or "")
        return [a for a in result if a]
    if isinstance(raw, str):
        return [a.strip() for a in raw.split(";") if a.strip()]
    return []


def _build_master_prompt(email: InboundEmail) -> str:
    """Compose the master prompt that kicks off the Vela agent loop."""
    return f"""\
A new email has arrived at the Vela shared mailbox. Process it following
your standard workflow.

── INBOUND EMAIL ──
Message ID: {email.message_id}
Conversation ID: {email.conversation_id}
From: {email.from_address} ({email.from_name})
To: {', '.join(email.to_addresses)}
CC: {', '.join(email.cc_addresses)}
Subject: {email.subject}
Received: {email.received_at.isoformat()}
Importance: {email.importance}

Body:
{email.body_text[:6000]}
── END EMAIL ──

Follow your standard workflow:
1. Parse the email with `parse_email` and `identify_attorney`
2. Load the attorney's preferences with `get_preferences`
3. Process any "Vela: ..." preference commands
4. Evaluate escalation with `evaluate_escalation`
5. If no escalation: find available slots with `find_available_slots`
6. Draft a reply with `draft_reply`
7. Send it with `send_reply` (if confidence meets threshold) or escalate

The Vela shared mailbox is: {settings.vela_mailbox}
"""

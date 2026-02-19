"""Microsoft Graph API client for reading emails, calendars, and sending mail.

Uses ``DefaultAzureCredential`` so the same code works with:
- ``az login`` during local development
- Managed Identity in production
- Client-secret credentials when AZURE_CLIENT_ID/SECRET/TENANT are set

Required Graph Permissions (Application):
    Mail.Read, Mail.Send, Calendars.Read, User.Read.All
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.identity import DefaultAzureCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import (
    CalendarViewRequestBuilder,
)
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)

logger = logging.getLogger("strapped.graph")

_GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


class StrappedGraphClient:
    """High-level facade over the MS Graph SDK for Strapped AI."""

    def __init__(self) -> None:
        credential = DefaultAzureCredential()
        self._client = GraphServiceClient(credentials=credential, scopes=_GRAPH_SCOPES)

    # ── Email: Read ──────────────────────────────────────────────────────

    async def get_recent_emails(
        self,
        user_email: str,
        count: int = 20,
        since_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Fetch the most recent emails from a user's inbox."""
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        filter_str = f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["subject", "from", "receivedDateTime", "bodyPreview",
                    "isRead", "importance", "hasAttachments", "toRecipients"],
            filter=filter_str,
            orderby=["receivedDateTime desc"],
            top=count,
        )
        config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=params,
        )
        result = await self._client.users.by_user_id(user_email).messages.get(config)

        emails: list[dict[str, Any]] = []
        for msg in result.value or []:
            from_addr = ""
            from_name = ""
            if msg.from_ and msg.from_.email_address:
                from_addr = msg.from_.email_address.address or ""
                from_name = msg.from_.email_address.name or ""

            emails.append({
                "subject": msg.subject or "(no subject)",
                "from_address": from_addr,
                "from_name": from_name,
                "received_at": msg.received_date_time.isoformat() if msg.received_date_time else "",
                "preview": msg.body_preview or "",
                "is_read": msg.is_read or False,
                "importance": msg.importance.value if msg.importance else "normal",
                "has_attachments": msg.has_attachments or False,
            })

        logger.info("Fetched %d emails for %s", len(emails), user_email)
        return emails

    # ── Calendar: Read ───────────────────────────────────────────────────

    async def get_events(
        self,
        user_email: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Retrieve calendar events for *user_email* in the given window."""
        params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=start.isoformat(),
            end_date_time=end.isoformat(),
            select=["subject", "start", "end", "location", "attendees",
                    "isAllDay", "bodyPreview", "organizer"],
            orderby=["start/dateTime"],
            top=50,
        )
        config = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetRequestConfiguration(
            query_parameters=params,
        )
        result = await self._client.users.by_user_id(user_email).calendar_view.get(config)

        events: list[dict[str, Any]] = []
        for ev in result.value or []:
            start_dt = ev.start.date_time if ev.start else ""
            end_dt = ev.end.date_time if ev.end else ""
            location = ev.location.display_name if ev.location else ""
            organizer = ""
            if ev.organizer and ev.organizer.email_address:
                organizer = ev.organizer.email_address.name or ev.organizer.email_address.address or ""

            attendees = [
                a.email_address.name or a.email_address.address
                for a in (ev.attendees or [])
                if a.email_address
            ]

            events.append({
                "subject": ev.subject or "(no subject)",
                "start": start_dt,
                "end": end_dt,
                "location": location,
                "attendees": attendees,
                "organizer": organizer,
                "is_all_day": ev.is_all_day or False,
                "notes": (ev.body_preview or "")[:200],
            })

        logger.info("Fetched %d events for %s", len(events), user_email)
        return events

    # ── Mail: Send ───────────────────────────────────────────────────────

    async def send_mail(
        self,
        from_mailbox: str,
        to_addresses: list[str],
        subject: str,
        body_html: str,
    ) -> None:
        """Send an email from the Strapped shared mailbox."""
        message = Message(
            subject=subject,
            body=ItemBody(content_type=BodyType.Html, content=body_html),
            to_recipients=[
                Recipient(email_address=GraphEmailAddress(address=addr))
                for addr in to_addresses
            ],
        )
        body = SendMailPostRequestBody(message=message, save_to_sent_items=True)
        await self._client.users.by_user_id(from_mailbox).send_mail.post(body)
        logger.info("Mail sent from %s to %s", from_mailbox, to_addresses)

"""Microsoft Graph API client for calendar and email operations.

Uses ``DefaultAzureCredential`` so the same code works with:
- ``az login`` during local development
- Managed Identity in Azure Function Apps
- Client-secret credentials when AZURE_CLIENT_ID/SECRET/TENANT are set

Required Graph Permissions (Application):
    Calendars.ReadWrite, Mail.Send, User.Read.All
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from azure.identity import DefaultAzureCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.event import Event
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import (
    CalendarViewRequestBuilder,
)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)

from core.models import CalendarEvent, TimeSlot

logger = logging.getLogger("strapped.graph")

_GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


class StrappedGraphClient:
    """High-level facade over the MS Graph SDK for Strapped AI operations."""

    def __init__(self) -> None:
        credential = DefaultAzureCredential()
        self._client = GraphServiceClient(credentials=credential, scopes=_GRAPH_SCOPES)

    # ── Calendar: Read ───────────────────────────────────────────────────────

    async def get_events(
        self,
        user_email: str,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        """Retrieve calendar events for *user_email* in the given window."""
        params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=start.isoformat(),
            end_date_time=end.isoformat(),
            select=["subject", "start", "end", "location", "attendees", "isAllDay", "showAs"],
            orderby=["start/dateTime"],
            top=50,
        )
        config = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetRequestConfiguration(
            query_parameters=params,
        )
        result = await self._client.users.by_user_id(user_email).calendar_view.get(config)

        events: list[CalendarEvent] = []
        for ev in result.value or []:
            events.append(
                CalendarEvent(
                    event_id=ev.id or "",
                    subject=ev.subject or "(no subject)",
                    start=_parse_graph_dt(ev.start),
                    end=_parse_graph_dt(ev.end),
                    location=ev.location.display_name if ev.location else "",
                    attendees=[
                        a.email_address.address
                        for a in (ev.attendees or [])
                        if a.email_address and a.email_address.address
                    ],
                    is_all_day=ev.is_all_day or False,
                    show_as=ev.show_as.value if ev.show_as else "busy",
                )
            )
        logger.info("Fetched %d events for %s", len(events), user_email)
        return events

    async def find_available_slots(
        self,
        user_email: str,
        date: datetime,
        duration_minutes: int,
        working_start: str = "08:00",
        working_end: str = "18:00",
        buffer_before: int = 15,
        buffer_after: int = 10,
        tz_name: str = "America/New_York",
    ) -> list[TimeSlot]:
        """Find available slots on *date* for a meeting of *duration_minutes*."""
        import pytz

        tz = pytz.timezone(tz_name)
        day_start = tz.localize(
            datetime.combine(date.date(), datetime.strptime(working_start, "%H:%M").time())
        )
        day_end = tz.localize(
            datetime.combine(date.date(), datetime.strptime(working_end, "%H:%M").time())
        )

        events = await self.get_events(user_email, day_start, day_end)
        busy: list[tuple[datetime, datetime]] = []
        for ev in events:
            if ev.show_as in ("busy", "tentative", "oof"):
                buf_start = ev.start - timedelta(minutes=buffer_before)
                buf_end = ev.end + timedelta(minutes=buffer_after)
                busy.append((buf_start, buf_end))

        busy.sort(key=lambda x: x[0])
        slots: list[TimeSlot] = []
        cursor = day_start

        for b_start, b_end in busy:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            if slot_end <= b_start:
                slots.append(TimeSlot(
                    start=cursor,
                    end=slot_end,
                    score=_score_slot(cursor, tz),
                    reason=_slot_reason(cursor),
                ))
            cursor = max(cursor, b_end)

        final_slot_end = cursor + timedelta(minutes=duration_minutes)
        if final_slot_end <= day_end:
            slots.append(TimeSlot(
                start=cursor,
                end=final_slot_end,
                score=_score_slot(cursor, tz),
                reason=_slot_reason(cursor),
            ))

        slots.sort(key=lambda s: s.score, reverse=True)
        return slots

    # ── Calendar: Write ──────────────────────────────────────────────────────

    async def create_event(
        self,
        organizer_email: str,
        subject: str,
        start: datetime,
        end: datetime,
        attendees: list[str],
        body_html: str = "",
        location: str = "",
        tz_name: str = "America/New_York",
    ) -> str:
        """Create a calendar event and return its Graph ID."""
        event = Event(
            subject=subject,
            start=DateTimeTimeZone(date_time=start.strftime("%Y-%m-%dT%H:%M:%S"), time_zone=tz_name),
            end=DateTimeTimeZone(date_time=end.strftime("%Y-%m-%dT%H:%M:%S"), time_zone=tz_name),
            attendees=[
                Attendee(email_address=GraphEmailAddress(address=addr))
                for addr in attendees
            ],
            body=ItemBody(content_type=BodyType.Html, content=body_html) if body_html else None,
        )
        created = await self._client.users.by_user_id(organizer_email).events.post(event)
        event_id = created.id if created else ""
        logger.info("Created event %s for %s", event_id, organizer_email)
        return event_id

    # ── Mail: Send ───────────────────────────────────────────────────────────

    async def send_mail(
        self,
        from_mailbox: str,
        to_addresses: list[str],
        subject: str,
        body_html: str,
        cc_addresses: list[str] | None = None,
    ) -> None:
        """Send an email from the Strapped shared mailbox."""
        message = Message(
            subject=subject,
            body=ItemBody(content_type=BodyType.Html, content=body_html),
            to_recipients=[
                Recipient(email_address=GraphEmailAddress(address=addr))
                for addr in to_addresses
            ],
            cc_recipients=[
                Recipient(email_address=GraphEmailAddress(address=addr))
                for addr in (cc_addresses or [])
            ],
        )
        body = SendMailPostRequestBody(message=message, save_to_sent_items=True)
        await self._client.users.by_user_id(from_mailbox).send_mail.post(body)
        logger.info("Mail sent from %s to %s", from_mailbox, to_addresses)

    # ── User lookup ──────────────────────────────────────────────────────────

    async def get_user_display_name(self, email: str) -> str:
        try:
            user = await self._client.users.by_user_id(email).get()
            return user.display_name or email
        except Exception:
            return email


# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_graph_dt(dt: DateTimeTimeZone | None) -> datetime:
    if not dt or not dt.date_time:
        return datetime.now(timezone.utc)
    from dateutil.parser import parse as dt_parse
    return dt_parse(dt.date_time).replace(tzinfo=timezone.utc)


def _score_slot(start: datetime, tz: Any) -> float:
    """Heuristic quality score — prefers mid-morning and mid-afternoon."""
    hour = start.astimezone(tz).hour
    if 9 <= hour <= 11:
        return 1.0
    if 14 <= hour <= 16:
        return 0.9
    if hour == 8 or hour == 13:
        return 0.7
    return 0.5


def _slot_reason(start: datetime) -> str:
    hour = start.hour
    if 9 <= hour <= 11:
        return "Prime morning focus time"
    if 14 <= hour <= 16:
        return "Productive afternoon window"
    if hour < 9:
        return "Early-morning slot"
    return "Available slot"

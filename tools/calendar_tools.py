"""Calendar orchestration Amplifier tools.

Wraps the Graph client so the LLM agent can read calendars, find free slots,
and create events — all while respecting attorney preferences and firm-wide
court blocks.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from amplifier_core import ToolResult

from core.graph_client import StrappedGraphClient
from core.models import AttorneyPreferences

logger = logging.getLogger("strapped.tools.calendar")


class CheckCalendarTool:
    """Retrieve upcoming events for an attorney within a date range."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "check_calendar"

    @property
    def description(self) -> str:
        return (
            "Fetch calendar events for an attorney between two dates. "
            "Returns a list of events with subject, start, end, and attendees."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attorney_email": {"type": "string", "description": "Attorney's email"},
                "start_date": {"type": "string", "description": "ISO date/datetime"},
                "end_date": {"type": "string", "description": "ISO date/datetime"},
            },
            "required": ["attorney_email", "start_date", "end_date"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            start = datetime.fromisoformat(input["start_date"])
            end = datetime.fromisoformat(input["end_date"])
            events = await self._graph.get_events(input["attorney_email"], start, end)
            return ToolResult(
                success=True,
                output=json.dumps(
                    [e.model_dump(mode="json") for e in events],
                    default=str,
                ),
            )
        except Exception as exc:
            logger.exception("check_calendar failed")
            return ToolResult(success=False, error={"message": str(exc)})


class FindAvailableSlotsTool:
    """Find open time slots on a given date for an attorney."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "find_available_slots"

    @property
    def description(self) -> str:
        return (
            "Find available meeting slots on a specific date for an attorney, "
            "respecting their working hours, buffer preferences, and existing "
            "commitments. Returns ranked slots with quality scores."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attorney_email": {"type": "string"},
                "date": {"type": "string", "description": "ISO date, e.g. 2025-03-15"},
                "duration_minutes": {"type": "integer", "default": 60},
                "working_hours_start": {"type": "string", "default": "08:00"},
                "working_hours_end": {"type": "string", "default": "18:00"},
                "buffer_before": {"type": "integer", "default": 15},
                "buffer_after": {"type": "integer", "default": 10},
                "timezone": {"type": "string", "default": "America/New_York"},
            },
            "required": ["attorney_email", "date"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            date = datetime.fromisoformat(input["date"])
            slots = await self._graph.find_available_slots(
                user_email=input["attorney_email"],
                date=date,
                duration_minutes=input.get("duration_minutes", 60),
                working_start=input.get("working_hours_start", "08:00"),
                working_end=input.get("working_hours_end", "18:00"),
                buffer_before=input.get("buffer_before", 15),
                buffer_after=input.get("buffer_after", 10),
                tz_name=input.get("timezone", "America/New_York"),
            )
            return ToolResult(
                success=True,
                output=json.dumps(
                    [s.model_dump(mode="json") for s in slots[:5]],
                    default=str,
                ),
            )
        except Exception as exc:
            logger.exception("find_available_slots failed")
            return ToolResult(success=False, error={"message": str(exc)})


class CreateCalendarEventTool:
    """Create a calendar event via Graph API."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "create_calendar_event"

    @property
    def description(self) -> str:
        return (
            "Create a calendar event for an attorney with specified attendees, "
            "time, and details. Returns the created event ID."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "organizer_email": {"type": "string"},
                "subject": {"type": "string"},
                "start": {"type": "string", "description": "ISO datetime"},
                "end": {"type": "string", "description": "ISO datetime"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Email addresses of attendees",
                },
                "body_html": {"type": "string", "default": ""},
                "location": {"type": "string", "default": ""},
                "timezone": {"type": "string", "default": "America/New_York"},
            },
            "required": ["organizer_email", "subject", "start", "end", "attendees"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            start = datetime.fromisoformat(input["start"])
            end = datetime.fromisoformat(input["end"])
            event_id = await self._graph.create_event(
                organizer_email=input["organizer_email"],
                subject=input["subject"],
                start=start,
                end=end,
                attendees=input["attendees"],
                body_html=input.get("body_html", ""),
                location=input.get("location", ""),
                tz_name=input.get("timezone", "America/New_York"),
            )
            return ToolResult(
                success=True,
                output=json.dumps({"event_id": event_id, "status": "created"}),
            )
        except Exception as exc:
            logger.exception("create_calendar_event failed")
            return ToolResult(success=False, error={"message": str(exc)})


class CheckMultiPartyAvailabilityTool:
    """Find slots where multiple attendees are all free."""

    def __init__(self, graph: StrappedGraphClient) -> None:
        self._graph = graph

    @property
    def name(self) -> str:
        return "check_multi_party_availability"

    @property
    def description(self) -> str:
        return (
            "Find time slots where ALL specified attendees are available. "
            "Checks each person's calendar and intersects free windows."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attendee_emails": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "date": {"type": "string"},
                "duration_minutes": {"type": "integer", "default": 60},
                "timezone": {"type": "string", "default": "America/New_York"},
            },
            "required": ["attendee_emails", "date"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            date = datetime.fromisoformat(input["date"])
            duration = input.get("duration_minutes", 60)
            tz = input.get("timezone", "America/New_York")

            all_slots: list[list[dict]] = []
            for email in input["attendee_emails"]:
                slots = await self._graph.find_available_slots(
                    user_email=email,
                    date=date,
                    duration_minutes=duration,
                    tz_name=tz,
                )
                all_slots.append(
                    [{"start": s.start.isoformat(), "end": s.end.isoformat()} for s in slots]
                )

            # Intersect: keep only slots that appear in every attendee's list
            if not all_slots:
                return ToolResult(success=True, output=json.dumps([]))

            common = all_slots[0]
            for person_slots in all_slots[1:]:
                person_starts = {s["start"] for s in person_slots}
                common = [s for s in common if s["start"] in person_starts]

            return ToolResult(
                success=True,
                output=json.dumps(common[:5], default=str),
            )
        except Exception as exc:
            logger.exception("check_multi_party_availability failed")
            return ToolResult(success=False, error={"message": str(exc)})

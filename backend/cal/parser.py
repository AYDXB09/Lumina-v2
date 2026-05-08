"""
iCal parser — fetches an .ics URL and returns a list of expanded event dicts.

Handles:
  • Single events (VEVENT with DTSTART / DTEND)
  • All-day events (DATE values)
  • Recurring events — RRULE expanded into individual occurrences
    using python-dateutil's rrule engine

The window parameter controls how far ahead/behind to expand events.
Default: 7 days back to 60 days forward (catches past due-dates + upcoming).

Output format per event:
{
  "uid":          str,
  "title":        str,
  "start":        ISO-8601 string (with timezone),
  "end":          ISO-8601 string (with timezone),
  "all_day":      bool,
  "location":     str | None,
  "description":  str | None,
  "type":         "class" | "assignment_due" | "personal" | "other",
  "url":          str | None,
}
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

import httpx
from icalendar import Calendar, vDatetime, vDate
from dateutil.rrule import rruleset, rrulestr

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Window defaults                                                     #
# ------------------------------------------------------------------ #

WINDOW_DAYS = {
    "1day":    (0, 1),
    "1week":   (7, 7),
    "2weeks":  (7, 14),
    "1month":  (7, 31),
    "3months": (7, 92),
    "1year":   (7, 365),
}


def _to_datetime(val, tzinfo=timezone.utc) -> Optional[datetime]:
    """Normalise a vDatetime / vDate / datetime / date to an aware datetime."""
    if val is None:
        return None
    # Unwrap icalendar value types
    dt = val.dt if hasattr(val, "dt") else val
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzinfo)
        return dt
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)
    return None


def _classify_event(title: str, description: str) -> str:
    """Best-effort classification of an event type."""
    t = (title or "").lower()
    d = (description or "").lower()
    if any(k in t or k in d for k in ("class", "lecture", "lesson", "session", "meeting")):
        return "class"
    if any(k in t for k in ("assignment", "due", "submit", "submission", "homework", "hw")):
        return "assignment_due"
    return "personal"


def _event_to_dict(component, start_dt: datetime, end_dt: datetime) -> dict:
    """Convert a VEVENT component + resolved dates to the Lumina event dict."""
    title = str(component.get("SUMMARY", "")).strip()
    description = str(component.get("DESCRIPTION", "")).strip()
    location = str(component.get("LOCATION", "")).strip() or None
    uid = str(component.get("UID", "")).strip()
    url = str(component.get("URL", "")).strip() or None

    all_day = not isinstance(
        (component.get("DTSTART").dt if component.get("DTSTART") else None),
        datetime
    )

    return {
        "uid":         uid,
        "title":       title,
        "start":       start_dt.isoformat(),
        "end":         end_dt.isoformat() if end_dt else start_dt.isoformat(),
        "all_day":     all_day,
        "location":    location,
        "description": description or None,
        "type":        _classify_event(title, description),
        "url":         url,
    }


async def fetch_and_parse(
    ical_url: str,
    fetch_window: str = "1week",
) -> list[dict]:
    """
    Fetch an .ics URL and return expanded events within the fetch window.

    fetch_window: key from WINDOW_DAYS — e.g. "1week", "1month"
    Returns list of event dicts sorted by start time.
    """
    days_back, days_forward = WINDOW_DAYS.get(fetch_window, (7, 7))
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days_back)
    window_end   = now + timedelta(days=days_forward)

    # Normalise webcal:// → https:// (Apple iCal, some Google links use this protocol)
    fetch_url = ical_url
    if fetch_url.startswith("webcal://"):
        fetch_url = "https://" + fetch_url[len("webcal://"):]
    elif fetch_url.startswith("webcals://"):
        fetch_url = "https://" + fetch_url[len("webcals://"):]

    # Fetch .ics content
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(fetch_url, headers={"User-Agent": "Lumina/2.0 (calendar sync)"})
            resp.raise_for_status()
            ical_bytes = resp.content
    except httpx.HTTPStatusError as e:
        logger.error("iCal fetch HTTP error %s for %s: %s", e.response.status_code, fetch_url, e)
        raise ValueError(f"Calendar URL returned {e.response.status_code}. Check the URL is a public .ics link.")
    except Exception as e:
        logger.error("Failed to fetch iCal URL %s: %s", fetch_url, e)
        raise

    # Parse
    try:
        cal = Calendar.from_ical(ical_bytes)
    except Exception as e:
        logger.error("Failed to parse iCal content: %s", e)
        raise ValueError(f"Invalid iCal data: {e}")

    events: list[dict] = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("DTSTART")
        dtend   = component.get("DTEND") or component.get("DUE")

        if not dtstart:
            continue

        start_dt = _to_datetime(dtstart)
        end_dt   = _to_datetime(dtend) if dtend else None
        duration = (end_dt - start_dt) if end_dt and start_dt else timedelta(hours=1)

        rrule_prop = component.get("RRULE")

        if rrule_prop:
            # Expand recurring event within the window
            try:
                rrule_str = f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:{rrule_prop.to_ical().decode()}"
                rs = rruleset()
                for rule in rrulestr(rrule_str, ignoretz=False, dtstart=start_dt):
                    pass  # just validate
                # Use rrulestr directly
                from dateutil.rrule import rrulestr as rs2
                rule_iter = rs2(
                    rrule_prop.to_ical().decode(),
                    dtstart=start_dt,
                    ignoretz=False,
                )
                for occurrence in rule_iter:
                    # Make timezone-aware if needed
                    if occurrence.tzinfo is None:
                        occurrence = occurrence.replace(tzinfo=timezone.utc)
                    if occurrence > window_end:
                        break
                    if occurrence + duration < window_start:
                        continue
                    occ_end = occurrence + duration
                    events.append(_event_to_dict(component, occurrence, occ_end))
            except Exception as e:
                logger.debug("RRULE expansion failed for event, using base date: %s", e)
                if start_dt and window_start <= start_dt <= window_end:
                    events.append(_event_to_dict(component, start_dt, end_dt or start_dt + timedelta(hours=1)))
        else:
            # Single event — include if within window
            if start_dt and window_start <= start_dt <= window_end:
                events.append(_event_to_dict(component, start_dt, end_dt or start_dt + timedelta(hours=1)))

    # Sort by start time
    events.sort(key=lambda e: e["start"])
    logger.info("Parsed %d events from %s", len(events), ical_url)
    return events

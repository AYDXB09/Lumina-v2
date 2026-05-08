"""
Calendar routes.

GET  /api/calendar/sources           — list user's calendar sources
POST /api/calendar/sources           — add a personal calendar URL
DELETE /api/calendar/sources/{id}    — remove a personal calendar
GET  /api/calendar/events            — get cached events (fetches if needed)
POST /api/calendar/sync              — force re-fetch all calendars
GET  /api/calendar/events/prompt     — formatted text for AI prompt injection
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.middleware import get_current_student
from cal.parser import fetch_and_parse, WINDOW_DAYS
from db.client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# How stale a cache entry must be before auto-refresh (per sync_frequency setting)
STALE_HOURS = {
    "query":   0,      # always re-fetch on query
    "login":   99999,  # only fetch once (manual sync)
    "daily":   24,
    "weekly":  168,
    "monthly": 720,
}


# ------------------------------------------------------------------ #
# Models                                                              #
# ------------------------------------------------------------------ #

class AddSourceRequest(BaseModel):
    label: str
    url: str


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

async def _get_sources(user_id: str) -> list[dict]:
    """Return list of calendar sources from users.calendar_sources."""
    sb = get_supabase()
    result = sb.table("users").select("calendar_sources").eq("id", user_id).single().execute()
    if not result.data:
        return []
    return result.data.get("calendar_sources") or []


async def _save_sources(user_id: str, sources: list[dict]):
    sb = get_supabase()
    sb.table("users").update({"calendar_sources": sources}).eq("id", user_id).execute()


async def _fetch_and_cache(user_id: str, source: dict, fetch_window: str) -> tuple[list[dict], str | None]:
    """
    Fetch events for one source and upsert into calendar_cache.
    Returns (events, error_message).  error_message is None on success.
    Only writes to cache on success — never caches empty-due-to-error results.
    """
    try:
        events = await fetch_and_parse(source["url"], fetch_window)
    except Exception as e:
        logger.warning("Calendar fetch failed for source %s: %s", source["id"], e)
        return [], str(e)

    sb = get_supabase()
    sb.table("calendar_cache").upsert({
        "user_id":    user_id,
        "source_id":  source["id"],
        "label":      source.get("label", ""),
        "events":     events,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,source_id").execute()

    return events, None


def _cache_is_stale(fetched_at_str: str | None, sync_frequency: str) -> bool:
    """Return True if the cache should be refreshed."""
    stale_hours = STALE_HOURS.get(sync_frequency, 0)
    if stale_hours == 0:
        return True  # "query" — always refresh
    if not fetched_at_str:
        return True
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        return age_hours > stale_hours
    except Exception:
        return True


def _filter_events_to_window(events: list[dict], fetch_window: str) -> list[dict]:
    """Filter cached events to the requested window."""
    days_back, days_forward = WINDOW_DAYS.get(fetch_window, (7, 7))
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=days_back)).isoformat()
    window_end   = (now + timedelta(days=days_forward)).isoformat()
    return [e for e in events if window_start <= e.get("start", "") <= window_end]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@router.get("/sources")
async def list_sources(user=Depends(get_current_student)):
    sources = await _get_sources(user["sub"])
    return {"sources": sources}


@router.post("/sources")
async def add_source(body: AddSourceRequest, user=Depends(get_current_student)):
    """
    Add a personal calendar URL (.ics).
    Immediately fetches and caches events using the widest window (3 months)
    so the AI has data from the moment the calendar is connected.
    """
    sources = await _get_sources(user["sub"])

    # Avoid duplicates
    if any(s["url"] == body.url for s in sources):
        raise HTTPException(status_code=409, detail="Calendar URL already added")

    new_source = {
        "id":    str(uuid.uuid4()),
        "label": body.label.strip() or "My Calendar",
        "url":   body.url.strip(),
        "auto":  False,
    }
    sources.append(new_source)
    await _save_sources(user["sub"], sources)

    # Immediately cache events — use a wide window so AI has full context
    events, fetch_error = await _fetch_and_cache(user["sub"], new_source, "3months")

    return {
        "source":       new_source,
        "sources":      sources,
        "events_loaded": len(events),
        "fetch_error":  fetch_error,   # None on success, error string on failure
    }


@router.delete("/sources/{source_id}")
async def remove_source(source_id: str, user=Depends(get_current_student)):
    """Remove a personal calendar (cannot remove Canvas auto source)."""
    sources = await _get_sources(user["sub"])
    original = [s for s in sources if s["id"] == source_id]

    if not original:
        raise HTTPException(status_code=404, detail="Calendar source not found")
    if original[0].get("auto"):
        raise HTTPException(status_code=403, detail="Cannot remove auto-connected Canvas calendar")

    sources = [s for s in sources if s["id"] != source_id]
    await _save_sources(user["sub"], sources)

    # Remove cached events for this source
    sb = get_supabase()
    sb.table("calendar_cache").delete().eq("user_id", user["sub"]).eq("source_id", source_id).execute()

    return {"message": "Calendar removed", "sources": sources}


@router.get("/events")
async def get_events(
    fetch_window: str = "1week",
    sync_frequency: str = "query",
    user=Depends(get_current_student),
):
    """
    Return calendar events for the student.
    Re-fetches from source if cache is stale per sync_frequency.
    fetch_window: 1day | 1week | 2weeks | 1month | 3months | 1year
    sync_frequency: query | login | daily | weekly | monthly
    """
    sb = get_supabase()
    sources = await _get_sources(user["sub"])

    if not sources:
        return {"events": [], "sources": [], "message": "No calendars connected"}

    # Load existing cache rows
    cache_result = sb.table("calendar_cache").select(
        "source_id, events, fetched_at"
    ).eq("user_id", user["sub"]).execute()
    cache_map = {r["source_id"]: r for r in (cache_result.data or [])}

    all_events: list[dict] = []

    for source in sources:
        cached = cache_map.get(source["id"])
        if cached and not _cache_is_stale(cached.get("fetched_at"), sync_frequency):
            # Use cache
            events = _filter_events_to_window(cached["events"], fetch_window)
        else:
            # Fetch fresh
            events, _ = await _fetch_and_cache(user["sub"], source, fetch_window)
            events = _filter_events_to_window(events, fetch_window)

        # Tag each event with its source label
        for e in events:
            e["calendar"] = source.get("label", "Calendar")

        all_events.extend(events)

    all_events.sort(key=lambda e: e.get("start", ""))
    return {"events": all_events, "sources": [s["label"] for s in sources]}


@router.post("/sync")
async def sync_calendars(
    fetch_window: str = "1week",
    user=Depends(get_current_student),
):
    """Force re-fetch all calendar sources regardless of cache age."""
    sources = await _get_sources(user["sub"])
    if not sources:
        return {"message": "No calendars to sync", "total_events": 0}

    total = 0
    errors = []
    for source in sources:
        events, err = await _fetch_and_cache(user["sub"], source, fetch_window)
        total += len(events)
        if err:
            errors.append({"source": source.get("label", source["id"]), "error": err})

    return {
        "message":      f"Synced {len(sources)} calendar(s)",
        "total_events": total,
        "errors":       errors,
    }


@router.get("/events/prompt")
async def get_events_for_prompt(
    fetch_window: str = "1week",
    sync_frequency: str = "query",
    user=Depends(get_current_student),
):
    """
    Returns calendar events as formatted plain text for AI prompt injection.
    Used by the chat engine when building the system prompt for study plan queries.
    """
    result = await get_events(fetch_window, sync_frequency, user)
    events = result.get("events", [])

    if not events:
        return {"prompt_text": "", "event_count": 0}

    lines = ["CALENDAR EVENTS:"]
    from datetime import datetime as dt
    for e in events:
        try:
            start = dt.fromisoformat(e["start"])
            end   = dt.fromisoformat(e["end"])
            date_str  = start.strftime("%a %d %b")
            time_str  = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
            if e.get("all_day"):
                time_str = "All day"
            cal_label = f" [{e['calendar']}]" if e.get("calendar") else ""
            loc = f" @ {e['location']}" if e.get("location") else ""
            lines.append(f"  {date_str}  {time_str}  {e['title']}{loc}{cal_label}")
        except Exception:
            pass

    return {"prompt_text": "\n".join(lines), "event_count": len(events)}

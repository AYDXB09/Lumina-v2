"""
Study plan routes.

GET  /api/studyplan             — fetch cached plan, or generate one if none exists
POST /api/studyplan/regenerate  — force-regenerate from current assignments/exams/calendar
"""

import logging

from fastapi import APIRouter, Depends

from auth.middleware import get_current_student
from db.client import get_supabase
from studyplan.generator import generate_study_plan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/studyplan", tags=["studyplan"])


@router.get("")
async def get_study_plan(user=Depends(get_current_student)):
    sb = get_supabase()
    result = sb.table("study_plans").select("plan_data, generated_at").eq(
        "user_id", user["sub"]
    ).maybe_single().execute()

    # .maybe_single().execute() returns None (not a response with .data=None)
    # when zero rows match — must guard on `result` itself first.
    if result and result.data and result.data.get("plan_data"):
        return {
            "plan_data": result.data["plan_data"],
            "generated": False,
            "generated_at": result.data.get("generated_at"),
        }

    plan_data = await generate_study_plan(user["sub"])
    sb.table("study_plans").upsert({
        "user_id": user["sub"],
        "plan_data": plan_data,
    }, on_conflict="user_id").execute()

    return {"plan_data": plan_data, "generated": True}


@router.post("/regenerate")
async def regenerate_study_plan(user=Depends(get_current_student)):
    plan_data = await generate_study_plan(user["sub"])
    sb = get_supabase()
    sb.table("study_plans").upsert({
        "user_id": user["sub"],
        "plan_data": plan_data,
    }, on_conflict="user_id").execute()
    return {"plan_data": plan_data, "generated": True}

"""
Mind map routes.

GET  /api/mindmap/{course_id}   — fetch or auto-generate mind map graph data
PUT  /api/mindmap/{course_id}   — save updated graph data (user edits)
POST /api/mindmap/{course_id}/regenerate — force-regenerate from course content
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.middleware import get_current_student
from db.client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mindmap", tags=["mindmap"])


# ------------------------------------------------------------------ #
# Graph generation                                                    #
# ------------------------------------------------------------------ #

def _generate_graph(course_id: str, course_name: str, chunks: list[dict]) -> dict:
    """
    Build a topic tree from index_chunks.

    Structure:
      root (course name)
        ├── Pages
        │     ├── Page A
        │     └── Page B
        ├── Assignments
        │     ├── Assignment A [EXAM]
        │     └── Assignment B
        └── Quizzes & Exams
              ├── Quiz 1
              └── Midterm [EXAM]
    """
    root_id = str(uuid.uuid4())
    topics = [{
        "id":          root_id,
        "label":       course_name,
        "isRoot":      True,
        "parentId":    None,
        "evidenceScore": 0,
        "connections": [],
    }]

    CATEGORY_META = {
        "page":        ("📄 Pages",           None),
        "assignment":  ("📝 Assignments",     None),
        "quiz":        ("🧪 Quizzes & Exams", None),
        "announcement":("📢 Announcements",   None),
    }

    # Collect unique sources per type
    sources_by_type: dict[str, dict[str, str]] = {}  # type → { source_id: title }
    for chunk in chunks:
        stype = chunk.get("source_type", "")
        sid   = chunk.get("source_id",   "")
        meta  = chunk.get("metadata") or {}
        title = meta.get("title") or sid or "Untitled"
        if stype not in CATEGORY_META:
            continue
        if stype not in sources_by_type:
            sources_by_type[stype] = {}
        if sid not in sources_by_type[stype]:
            sources_by_type[stype][sid] = title

    # Create category + leaf nodes
    for stype, (cat_label, _) in CATEGORY_META.items():
        sources = sources_by_type.get(stype)
        if not sources:
            continue

        cat_id = str(uuid.uuid4())
        topics.append({
            "id":          cat_id,
            "label":       cat_label,
            "parentId":    root_id,
            "evidenceScore": 0,
            "connections": [],
        })

        for _sid, title in list(sources.items())[:40]:   # cap at 40 leaves per category
            leaf_id = str(uuid.uuid4())
            # Detect exam tag
            label = title
            # Truncate long titles
            if len(label) > 60:
                label = label[:57] + "…"
            topics.append({
                "id":          leaf_id,
                "label":       label,
                "parentId":    cat_id,
                "evidenceScore": 0,
                "connections": [],
            })

    return {"topics": topics, "generated": True}


# ------------------------------------------------------------------ #
# Models                                                              #
# ------------------------------------------------------------------ #

class SaveGraphRequest(BaseModel):
    graph_data: dict


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@router.get("/{course_id}")
async def get_mindmap(course_id: str, user=Depends(get_current_student)):
    """Return existing mind map or generate one from course content."""
    sb = get_supabase()

    # Check for saved mind map
    result = sb.table("mind_maps").select("graph_data, updated_at").eq(
        "user_id", user["sub"]
    ).eq("course_id", course_id).single().execute()

    if result.data and result.data.get("graph_data"):
        return {
            "graph_data": result.data["graph_data"],
            "generated":  False,
            "updated_at": result.data.get("updated_at"),
        }

    # Generate from index_chunks
    chunks = sb.table("index_chunks").select(
        "source_type, source_id, metadata"
    ).eq("course_id", course_id).execute()

    # Get course name
    course_row = sb.table("courses").select("name").eq("id", course_id).single().execute()
    course_name = (course_row.data or {}).get("name", "Course")

    if not chunks.data:
        return {"graph_data": {"topics": []}, "generated": True}

    graph_data = _generate_graph(course_id, course_name, chunks.data or [])

    # Persist the generated map so we don't regenerate every time
    sb.table("mind_maps").upsert({
        "user_id":    user["sub"],
        "course_id":  course_id,
        "graph_data": graph_data,
    }, on_conflict="user_id,course_id").execute()

    return {"graph_data": graph_data, "generated": True}


@router.put("/{course_id}")
async def save_mindmap(course_id: str, body: SaveGraphRequest, user=Depends(get_current_student)):
    """Save user-edited mind map."""
    sb = get_supabase()
    sb.table("mind_maps").upsert({
        "user_id":    user["sub"],
        "course_id":  course_id,
        "graph_data": body.graph_data,
    }, on_conflict="user_id,course_id").execute()
    return {"message": "Saved"}


@router.post("/{course_id}/regenerate")
async def regenerate_mindmap(course_id: str, user=Depends(get_current_student)):
    """Force-regenerate the mind map from current course content."""
    sb = get_supabase()

    chunks = sb.table("index_chunks").select(
        "source_type, source_id, metadata"
    ).eq("course_id", course_id).execute()

    course_row = sb.table("courses").select("name").eq("id", course_id).single().execute()
    course_name = (course_row.data or {}).get("name", "Course")

    graph_data = _generate_graph(course_id, course_name, chunks.data or [])

    sb.table("mind_maps").upsert({
        "user_id":    user["sub"],
        "course_id":  course_id,
        "graph_data": graph_data,
    }, on_conflict="user_id,course_id").execute()

    return {"graph_data": graph_data, "generated": True}

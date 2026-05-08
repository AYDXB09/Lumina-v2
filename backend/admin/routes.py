"""
Admin knowledge base routes.

Only accessible to users with canvas_role containing "Teacher" or "Admin".

POST   /api/admin/materials/upload   — upload + index a shared document
GET    /api/admin/materials          — list all shared materials for this school
DELETE /api/admin/materials/{id}     — remove a shared document
PATCH  /api/admin/materials/{id}     — update tags/metadata
"""

import logging
import uuid
from io import BytesIO
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from auth.middleware import get_current_student
from db.client import get_supabase
from rag.embedder import embed
from rag.indexer import _chunk_text, _build_tag_prefix

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/materials", tags=["admin"])

MAX_FILE_MB = 200   # per-file limit for admin/teacher uploads

ADMIN_ROLES = ("TeacherEnrollment", "TaEnrollment", "DesignerEnrollment", "AccountAdmin", "teacher", "admin")


def _require_admin(user: dict):
    """Raise 403 if the user is not an admin/teacher."""
    role = (user.get("canvas_role") or "").lower()
    if not any(r.lower() in role for r in ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Admin or teacher role required")


def _extract_text(content: bytes, filename: str) -> str:
    fn_lower = filename.lower()
    if fn_lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content))
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n\n".join(p.strip() for p in pages if p.strip())
        except Exception as e:
            raise ValueError(f"Could not extract PDF text: {e}")
    for enc in ("utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported file encoding.")


# ------------------------------------------------------------------ #
# Models                                                              #
# ------------------------------------------------------------------ #

class PatchTagsRequest(BaseModel):
    tags:     dict | None = None
    metadata: dict | None = None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@router.post("/upload")
async def upload_shared_material(
    file: UploadFile = File(...),
    # Tag fields from multipart form
    grade_levels:  str = Form("[]"),      # JSON array string e.g. "[6,7,8]"
    subjects:      str = Form("[]"),      # JSON array string e.g. '["Mathematics"]'
    doc_type:      str = Form("other"),   # exam_paper|notes|textbook|syllabus|other
    expiry_date:   str = Form(""),        # ISO date string YYYY-MM-DD or ""
    applicable:    str = Form("true"),    # "true" | "false"
    title:         str = Form(""),
    description:   str = Form(""),
    user=Depends(get_current_student),
):
    import json

    _require_admin(user)
    sb = get_supabase()

    # Get school_id for this user
    user_row = sb.table("users").select("school_id, canvas_role").eq("id", user["sub"]).single().execute()
    school_id = (user_row.data or {}).get("school_id")
    if not school_id:
        raise HTTPException(status_code=400, detail="User has no school_id")

    content = await file.read()
    mb = len(content) / (1024 * 1024)
    if mb > MAX_FILE_MB:
        raise HTTPException(status_code=413, detail=f"File too large ({mb:.1f} MB). Limit {MAX_FILE_MB} MB.")

    filename = file.filename or "upload"
    try:
        text = _extract_text(content, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in file.")

    # Parse tags
    try:
        grade_levels_list = json.loads(grade_levels)
    except Exception:
        grade_levels_list = []
    try:
        subjects_list = json.loads(subjects)
    except Exception:
        subjects_list = []

    tags = {
        "grade_levels": grade_levels_list,
        "subjects":     subjects_list,
        "doc_type":     doc_type or "other",
        "expiry_date":  expiry_date or None,
        "applicable":   applicable.lower() != "false",
    }
    metadata = {
        "title":       title or filename,
        "description": description or "",
        "source":      filename,
    }

    # Chunk + embed (prepend tag prefix so subject/grade context enters the vector)
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document appears empty after chunking.")

    # Build tag prefix for embedding (uses same helper as student materials)
    tag_prefix = _build_tag_prefix({
        "subjects":     subjects_list,
        "grade_levels": grade_levels_list,
        "doc_type":     doc_type,
    })
    embed_texts = [tag_prefix + c for c in chunks] if tag_prefix else chunks
    vectors = embed(embed_texts)

    # Store one row per chunk (original content, no prefix)
    rows = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        rows.append({
            "id":          str(uuid.uuid4()),
            "school_id":   school_id,
            "uploaded_by": user["sub"],
            "filename":    filename,
            "content":     chunk,
            "embedding":   vector,
            "tags":        {**tags, "chunk": i},
            "metadata":    {**metadata, "chunk": i, "total_chunks": len(chunks)},
        })

    sb.table("shared_materials").insert(rows).execute()
    logger.info("Admin indexed %d chunks for school=%s file=%s", len(rows), school_id, filename)

    return {
        "filename":  filename,
        "chunks":    len(rows),
        "tags":      tags,
        "metadata":  metadata,
    }


@router.get("")
async def list_shared_materials(user=Depends(get_current_student)):
    """List all shared materials for this user's school (deduplicated by filename)."""
    _require_admin(user)
    sb = get_supabase()

    user_row = sb.table("users").select("school_id").eq("id", user["sub"]).single().execute()
    school_id = (user_row.data or {}).get("school_id")
    if not school_id:
        return {"materials": []}

    # Get chunk-0 rows only (one per document)
    result = sb.table("shared_materials").select(
        "id, filename, tags, metadata, uploaded_at, uploaded_by"
    ).eq("school_id", school_id).order("uploaded_at", desc=True).execute()

    # Deduplicate by filename, keeping the first (most recent) occurrence
    seen = {}
    for row in (result.data or []):
        fn = row["filename"]
        if fn not in seen:
            seen[fn] = row

    return {"materials": list(seen.values())}


@router.delete("/{material_id}")
async def delete_shared_material(material_id: str, user=Depends(get_current_student)):
    """Delete all chunks for a shared material by its filename (looked up by id)."""
    _require_admin(user)
    sb = get_supabase()

    user_row = sb.table("users").select("school_id").eq("id", user["sub"]).single().execute()
    school_id = (user_row.data or {}).get("school_id")

    # Find the filename from any chunk with this id
    row = sb.table("shared_materials").select("filename").eq("id", material_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Material not found")

    filename = row.data["filename"]
    sb.table("shared_materials").delete().eq("school_id", school_id).eq("filename", filename).execute()
    return {"message": f"Deleted {filename}"}


@router.patch("/{material_id}")
async def patch_shared_material(
    material_id: str,
    body: PatchTagsRequest,
    user=Depends(get_current_student),
):
    """Update tags or metadata for all chunks of a document."""
    _require_admin(user)
    sb = get_supabase()

    user_row = sb.table("users").select("school_id").eq("id", user["sub"]).single().execute()
    school_id = (user_row.data or {}).get("school_id")

    row = sb.table("shared_materials").select("filename, tags, metadata").eq("id", material_id).single().execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Material not found")

    filename = row.data["filename"]
    updates = {}
    if body.tags is not None:
        # Merge new tags over existing (preserve chunk key)
        updates["tags"] = {**row.data.get("tags", {}), **body.tags}
    if body.metadata is not None:
        updates["metadata"] = {**row.data.get("metadata", {}), **body.metadata}

    if updates:
        sb.table("shared_materials").update(updates).eq("school_id", school_id).eq("filename", filename).execute()

    return {"message": "Updated"}

"""
Student material upload — PDF / text files indexed into pgvector.

POST /api/materials/upload   — upload + index one or more files (multipart/form-data)
GET  /api/materials          — list distinct files uploaded by this user
DELETE /api/materials/{filename} — remove a file and its index chunks
"""

import logging
import re
from io import BytesIO
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth.middleware import get_current_student
from db.client import get_supabase
from rag.indexer import index_student_material

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/materials", tags=["materials"])

MAX_FILE_MB = 50   # per-file limit for student uploads


# ------------------------------------------------------------------ #
# Text extraction                                                      #
# ------------------------------------------------------------------ #

def _extract_text_from_pdf(content: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)
    except Exception as e:
        logger.warning("pypdf extraction failed: %s", e)
        raise ValueError(f"Could not extract text from PDF: {e}")


def _extract_text(content: bytes, filename: str) -> str:
    """Extract text from file bytes based on extension."""
    fn_lower = filename.lower()
    if fn_lower.endswith(".pdf"):
        return _extract_text_from_pdf(content)
    # Plain text / markdown
    for enc in ("utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode file as text. Only PDF and UTF-8 text files are supported.")


# ------------------------------------------------------------------ #
# Filename tag extraction                                             #
# ------------------------------------------------------------------ #

# Map of lowercase tokens → canonical subject name
_SUBJECT_MAP = {
    "math":         "Mathematics",
    "maths":        "Mathematics",
    "mathematics":  "Mathematics",
    "calculus":     "Mathematics",
    "algebra":      "Mathematics",
    "geometry":     "Mathematics",
    "statistics":   "Mathematics",
    "stats":        "Mathematics",
    "physics":      "Physics",
    "chemistry":    "Chemistry",
    "chem":         "Chemistry",
    "biology":      "Biology",
    "bio":          "Biology",
    "english":      "English",
    "literature":   "Literature",
    "lit":          "Literature",
    "history":      "History",
    "geography":    "Geography",
    "geo":          "Geography",
    "economics":    "Economics",
    "econ":         "Economics",
    "business":     "Business",
    "computer":     "Computer Science",
    "cs":           "Computer Science",
    "science":      "Science",
    "spanish":      "Spanish",
    "french":       "French",
    "german":       "German",
    "chinese":      "Chinese",
    "mandarin":     "Mandarin",
    "japanese":     "Japanese",
    "art":          "Art",
    "music":        "Music",
    "pe":           "Physical Education",
    "psychology":   "Psychology",
    "psych":        "Psychology",
    "philosophy":   "Philosophy",
    "theory":       "Theory of Knowledge",
    "tok":          "Theory of Knowledge",
    "environmental": "Environmental Science",
    "enviro":       "Environmental Science",
}

_DOC_TYPE_KEYWORDS = {
    "exam_paper": ["exam", "test", "pastpaper", "past_paper", "mock", "assessment", "quiz"],
    "notes":      ["note", "notes", "summary", "revision", "review", "cheat_sheet", "cheatsheet"],
    "textbook":   ["textbook", "textbook", "chapter", "chap"],
    "syllabus":   ["syllabus", "curriculum", "outline", "guide", "specification"],
}


def _extract_tags_from_filename(filename: str) -> dict:
    """
    Infer subject, grade levels, and doc_type from a filename.

    Examples:
        "Math_Grade8_Exam2024.pdf"      → subjects: [Mathematics], grade_levels: [8], doc_type: exam_paper
        "IB_Chemistry_HL_Notes.pdf"     → subjects: [Chemistry], grade_levels: [], doc_type: notes
        "Biology_Gr9-10_Textbook.pdf"   → subjects: [Biology], grade_levels: [9, 10], doc_type: textbook
        "Physics_Syllabus_Grade11_12"   → subjects: [Physics], grade_levels: [11, 12], doc_type: syllabus
    """
    # Strip extension
    name = re.sub(r'\.[^.]+$', '', filename)
    name_lower = name.lower()

    # ---- Grade levels (6–12) ----
    # Note: no trailing \b — underscore is \w so \b won't fire between digit and _
    grade_levels = set()

    # Range patterns first: Grade11_12, Gr9-10, Year6-7
    range_patterns = [
        r'grade[\s_\-]?(\d{1,2})[\s_\-]+(\d{1,2})',
        r'gr[\s_\-]?(\d{1,2})[\s_\-]+(\d{1,2})',
        r'year[\s_\-]?(\d{1,2})[\s_\-]+(\d{1,2})',
    ]
    for pattern in range_patterns:
        for m in re.finditer(pattern, name_lower):
            lo, hi = int(m.group(1)), int(m.group(2))
            grade_levels.update(g for g in range(lo, hi + 1) if 6 <= g <= 12)

    # Single grade patterns (only if no range already found for that position)
    single_patterns = [
        r'grade[\s_\-]?(\d{1,2})',
        r'gr[\s_\-]?(\d{1,2})',
        r'year[\s_\-]?(\d{1,2})',
        r'(\d{1,2})th[\s_\-]?grade',
    ]
    for pattern in single_patterns:
        for m in re.finditer(pattern, name_lower):
            g = int(m.group(1))
            if 6 <= g <= 12:
                grade_levels.add(g)

    grade_levels = sorted(grade_levels)

    # ---- Doc type ----
    doc_type = None
    for dt, keywords in _DOC_TYPE_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            doc_type = dt
            break

    # ---- Subjects ----
    tokens = re.split(r'[\s_\-\.]+', name_lower)
    subjects = []
    for token in tokens:
        subj = _SUBJECT_MAP.get(token)
        if subj and subj not in subjects:
            subjects.append(subj)

    return {
        "subjects":     subjects,
        "grade_levels": grade_levels,
        "doc_type":     doc_type,  # None = not detected
    }


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@router.post("/upload")
async def upload_materials(
    files: List[UploadFile] = File(...),
    course_id: str = Form(None),
    user=Depends(get_current_student),
):
    """
    Upload one or more PDF / text files and index them for RAG search.
    Returns per-file results including auto-detected tags from filename.
    """
    results = []

    for file in files:
        content = await file.read()
        filename = file.filename or "upload"
        mb = len(content) / (1024 * 1024)

        # Size guard
        if mb > MAX_FILE_MB:
            results.append({
                "filename": filename,
                "ok": False,
                "error": f"File too large ({mb:.1f} MB). Limit is {MAX_FILE_MB} MB.",
            })
            continue

        # Text extraction
        try:
            text = _extract_text(content, filename)
        except ValueError as e:
            results.append({"filename": filename, "ok": False, "error": str(e)})
            continue

        if not text.strip():
            results.append({
                "filename": filename,
                "ok": False,
                "error": "No extractable text found.",
            })
            continue

        # Auto-tag from filename
        auto_tags = _extract_tags_from_filename(filename)

        # Build metadata — only include detected tags
        metadata: dict = {"original_filename": filename, "size_bytes": len(content)}
        if auto_tags["subjects"]:
            metadata["subjects"] = auto_tags["subjects"]
        if auto_tags["grade_levels"]:
            metadata["grade_levels"] = auto_tags["grade_levels"]
        if auto_tags["doc_type"]:
            metadata["doc_type"] = auto_tags["doc_type"]

        # Index
        try:
            chunks = await index_student_material(
                user_id=user["sub"],
                course_id=course_id or "",
                filename=filename,
                text=text,
                metadata=metadata,
            )
            logger.info(
                "Indexed %d chunks for user=%s file=%s tags=%s",
                chunks, user["sub"], filename, auto_tags,
            )
            results.append({
                "filename":   filename,
                "ok":         True,
                "chunks":     chunks,
                "size_bytes": len(content),
                "auto_tags":  auto_tags,
            })
        except Exception as e:
            logger.error("Indexing failed for %s: %s", filename, e)
            results.append({
                "filename": filename,
                "ok": False,
                "error": f"Indexing failed: {e}",
            })

    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "results":  results,
        "total":    len(results),
        "ok_count": ok_count,
    }


@router.get("")
async def list_materials(user=Depends(get_current_student)):
    """Return list of distinct files this user has uploaded."""
    sb = get_supabase()
    result = sb.table("student_materials").select(
        "filename, course_id, metadata, uploaded_at"
    ).eq("user_id", user["sub"]).order(
        "uploaded_at", desc=True
    ).execute()

    materials = []
    seen = set()
    for row in (result.data or []):
        fn = row["filename"]
        if fn in seen:
            continue
        seen.add(fn)
        meta = row.get("metadata") or {}
        materials.append({
            "filename":    fn,
            "course_id":   row.get("course_id"),
            "uploaded_at": row.get("uploaded_at"),
            "chunk_count": meta.get("chunk_count"),
            "auto_tags":   {
                "subjects":     meta.get("subjects", []),
                "grade_levels": meta.get("grade_levels", []),
                "doc_type":     meta.get("doc_type"),
            },
        })

    return {"materials": materials}


@router.delete("/{filename:path}")
async def delete_material(filename: str, user=Depends(get_current_student)):
    """Remove a file and all its index chunks."""
    sb = get_supabase()
    sb.table("student_materials").delete().eq(
        "user_id", user["sub"]
    ).eq("filename", filename).execute()
    return {"message": f"Deleted {filename}"}

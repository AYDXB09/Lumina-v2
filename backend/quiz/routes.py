"""
Adaptive quiz routes.

POST /api/quiz/start                — begin a quiz on a topic, returns first question
POST /api/quiz/{attempt_id}/answer  — grade the current question, update mastery
POST /api/quiz/{attempt_id}/next    — generate and return the next question
POST /api/quiz/{attempt_id}/finish  — finalize score, mark attempt complete
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.middleware import get_current_student
from db.client import get_supabase
from quiz.generator import generate_question, update_mastery

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class StartQuizRequest(BaseModel):
    course_id: str
    topic: str


class NextQuestionRequest(BaseModel):
    pass


class AnswerRequest(BaseModel):
    selected_index: int


def _public_question(q: dict) -> dict:
    """Strip correct_index before sending a question to the client."""
    return {k: v for k, v in q.items() if k != "correct_index"}


@router.post("/start")
async def start_quiz(body: StartQuizRequest, user=Depends(get_current_student)):
    question = await generate_question(user["sub"], body.course_id, body.topic)

    sb = get_supabase()
    row = sb.table("quiz_attempts").insert({
        "user_id": user["sub"],
        "course_id": body.course_id,
        "topic": body.topic,
        "questions": [question],
        "answers": [],
        "difficulty": question["difficulty"],
    }).execute().data[0]

    return {
        "attempt_id": row["id"],
        "question_number": 1,
        "question": _public_question(question),
        "mastery": question["mastery"],
    }


@router.post("/{attempt_id}/answer")
async def answer_quiz(attempt_id: str, body: AnswerRequest, user=Depends(get_current_student)):
    sb = get_supabase()
    attempt = sb.table("quiz_attempts").select("*").eq("id", attempt_id).eq(
        "user_id", user["sub"]
    ).maybe_single().execute()
    if not attempt or not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    row = attempt.data
    questions = row["questions"] or []
    answers = row["answers"] or []
    if not questions or len(answers) >= len(questions):
        raise HTTPException(status_code=400, detail="No unanswered question on this attempt")

    current_question = questions[len(answers)]  # the question this answer applies to
    correct = body.selected_index == current_question["correct_index"]
    answers.append({"selected_index": body.selected_index, "correct": correct})

    new_mastery = await update_mastery(user["sub"], row["course_id"], row["topic"], correct)

    sb.table("quiz_attempts").update({"answers": answers}).eq("id", attempt_id).execute()

    return {
        "correct": correct,
        "correct_index": current_question["correct_index"],
        "hint": current_question.get("hint", ""),
        "mastery": new_mastery,
        "answered_count": len(answers),
    }


@router.post("/{attempt_id}/next")
async def next_question(attempt_id: str, user=Depends(get_current_student)):
    sb = get_supabase()
    attempt = sb.table("quiz_attempts").select("*").eq("id", attempt_id).eq(
        "user_id", user["sub"]
    ).maybe_single().execute()
    if not attempt or not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    row = attempt.data
    questions = row["questions"] or []
    answers = row["answers"] or []
    if len(answers) < len(questions):
        raise HTTPException(status_code=400, detail="Answer the current question before requesting the next one")
    if len(questions) >= 20:
        raise HTTPException(status_code=400, detail="Maximum questions per attempt reached")

    prior_texts = [q["question"] for q in questions]
    question = await generate_question(
        user["sub"], row["course_id"], row["topic"], exclude_questions=prior_texts
    )
    questions.append(question)

    sb.table("quiz_attempts").update({
        "questions": questions,
        "difficulty": question["difficulty"],
    }).eq("id", attempt_id).execute()

    return {
        "attempt_id": attempt_id,
        "question_number": len(questions),
        "question": _public_question(question),
        "mastery": question["mastery"],
    }


@router.post("/{attempt_id}/finish")
async def finish_quiz(attempt_id: str, user=Depends(get_current_student)):
    sb = get_supabase()
    attempt = sb.table("quiz_attempts").select("*").eq("id", attempt_id).eq(
        "user_id", user["sub"]
    ).maybe_single().execute()
    if not attempt or not attempt.data:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    row = attempt.data
    answers = row["answers"] or []
    score = (sum(1 for a in answers if a["correct"]) / len(answers)) if answers else 0.0

    sb.table("quiz_attempts").update({"score": round(score, 4)}).eq("id", attempt_id).execute()

    return {
        "attempt_id": attempt_id,
        "score": round(score, 4),
        "total": len(answers),
        "correct_count": sum(1 for a in answers if a["correct"]),
    }

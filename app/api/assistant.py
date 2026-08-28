"""
app/api/assistant.py
─────────────────────
REST API for the conversational assistant.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.assistant_agent import ask_assistant
from app.database import get_db

router = APIRouter(prefix="/assistant", tags=["assistant"])


class QuestionRequest(BaseModel):
    question: str
    user_email: str = "mahmudunmiraz@gmail.com"


class AnswerResponse(BaseModel):
    question: str
    answer: str


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask the assistant a question about your opportunities in plain English.

    Examples:
    - "What are my top 5 opportunities right now?"
    - "Which deadlines are coming up in the next 30 days?"
    - "Show me the cheapest programmes I'm eligible for"
    - "Which scholarships cover Bangladeshi students?"
    """
    answer = await ask_assistant(
        question=request.question,
        db=db,
        user_email=request.user_email,
    )
    return AnswerResponse(question=request.question, answer=answer)

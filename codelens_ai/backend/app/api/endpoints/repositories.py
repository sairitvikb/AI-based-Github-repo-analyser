from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from groq import Groq

from app.core.config import settings
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.improvement import ImprovementListResponse
from app.schemas.repository import (
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    FileInsightListResponse,
    RepositoryDetailResponse,
    RepositorySummaryResponse,
    RiskListResponse,
)
from app.services.repository_service import RepositoryService

router = APIRouter()
service = RepositoryService()


@router.post("/analyze", response_model=AnalyzeRepositoryResponse, status_code=status.HTTP_201_CREATED)
def analyze_repository(payload: AnalyzeRepositoryRequest, db: Session = Depends(get_db)):
    return service.analyze_repository(db, payload)


@router.get("/repo/{repo_id}", response_model=RepositoryDetailResponse)
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    repository = service.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


@router.get("/repo/{repo_id}/files", response_model=FileInsightListResponse)
def get_repository_files(repo_id: int, db: Session = Depends(get_db)):
    return service.get_file_insights(db, repo_id)


@router.get("/repo/{repo_id}/summary", response_model=RepositorySummaryResponse)
def get_repository_summary(repo_id: int, db: Session = Depends(get_db)):
    return service.get_summary(db, repo_id)


@router.get("/repo/{repo_id}/risks", response_model=RiskListResponse)
def get_repository_risks(repo_id: int, db: Session = Depends(get_db)):
    return service.get_risks(db, repo_id)


@router.get("/repo/{repo_id}/improvements", response_model=ImprovementListResponse)
def get_improvements(repo_id: int, db: Session = Depends(get_db)):
    return service.get_improvements(db, repo_id)


@router.post("/repo/{repo_id}/chat", response_model=ChatResponse)
def chat_with_repository(repo_id: int, payload: ChatRequest, db: Session = Depends(get_db)):
    repository = service.get_repository(db, repo_id)
    files_response = service.get_file_insights(db, repo_id)

    file_items = files_response.files[:15]

    context = "\n\n".join(
        [f"{item.path}: {item.summary}" for item in file_items]
    )

    prompt = f"""
You are an elite repository assistant.

Repository: {repository.owner}/{repository.name}

Known files:
{context}

User question:
{payload.question}

Instructions:
- Answer naturally like ChatGPT
- Be clear, smart, concise
- Use repository evidence
- Mention file names when useful
- If uncertain, say so honestly
"""

    try:
        client = Groq(api_key=settings.groq_api_key)

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        answer = response.choices[0].message.content

        return ChatResponse(
            answer=answer,
            sources=[]
        )

    except Exception as exc:
        return ChatResponse(
            answer=f"Groq request failed: {str(exc)}",
            sources=[]
        )
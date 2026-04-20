# backend/app/schemas/improvement.py

from pydantic import BaseModel


class ImprovementItem(BaseModel):
    title: str
    category: str
    priority: str
    description: str
    rationale: str


class ImprovementListResponse(BaseModel):
    repo_id: int
    total: int
    improvements: list[ImprovementItem]
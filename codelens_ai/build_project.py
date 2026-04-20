from pathlib import Path

root = Path('/mnt/data/codelens_ai')
files = {
'backend/requirements.txt': '''fastapi==0.116.1
uvicorn[standard]==0.35.0
httpx==0.28.1
pydantic==2.11.7
pydantic-settings==2.10.1
sqlalchemy==2.0.43
chromadb==1.0.20
langchain==0.3.27
langchain-openai==0.3.32
langchain-community==0.3.27
pytest==8.4.1
pytest-asyncio==1.1.0
''',
'backend/.env.example': '''APP_NAME=CodeLens AI API
APP_ENV=development
APP_DEBUG=true
API_V1_PREFIX=/api/v1
DATABASE_URL=sqlite:///./codelens.db
CHROMA_PERSIST_DIRECTORY=./chroma_db
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_TOKEN=
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MAX_FILE_BYTES=150000
MAX_FILES_TO_ANALYZE=150
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
''',
'backend/app/__init__.py': '',
'backend/app/main.py': '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.session import init_db

configure_logging()
init_db()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CodeLens AI API is running"}
''',
'backend/app/api/__init__.py': '',
'backend/app/api/routes.py': '''from fastapi import APIRouter

from app.api.endpoints import health, repositories

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(repositories.router, tags=["repositories"])
''',
'backend/app/api/endpoints/__init__.py': '',
'backend/app/api/endpoints/health.py': '''from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
''',
'backend/app/api/endpoints/repositories.py': '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
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
def analyze_repository(payload: AnalyzeRepositoryRequest, db: Session = Depends(get_db)) -> AnalyzeRepositoryResponse:
    return service.analyze_repository(db, payload)


@router.get("/repo/{repo_id}", response_model=RepositoryDetailResponse)
def get_repository(repo_id: int, db: Session = Depends(get_db)) -> RepositoryDetailResponse:
    repository = service.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


@router.get("/repo/{repo_id}/files", response_model=FileInsightListResponse)
def get_repository_files(repo_id: int, db: Session = Depends(get_db)) -> FileInsightListResponse:
    return service.get_file_insights(db, repo_id)


@router.get("/repo/{repo_id}/summary", response_model=RepositorySummaryResponse)
def get_repository_summary(repo_id: int, db: Session = Depends(get_db)) -> RepositorySummaryResponse:
    summary = service.get_summary(db, repo_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary


@router.get("/repo/{repo_id}/risks", response_model=RiskListResponse)
def get_repository_risks(repo_id: int, db: Session = Depends(get_db)) -> RiskListResponse:
    return service.get_risks(db, repo_id)


@router.post("/repo/{repo_id}/chat", response_model=ChatResponse)
def chat_with_repository(repo_id: int, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return service.chat(db, repo_id, payload)
''',
'backend/app/core/config.py': '''from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeLens AI API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./codelens.db"
    chroma_persist_directory: str = "./chroma_db"
    github_api_base_url: str = "https://api.github.com"
    github_token: str = ""
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    max_file_bytes: int = 150000
    max_files_to_analyze: int = 150
    chunk_size: int = 1200
    chunk_overlap: int = 200
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
''',
'backend/app/core/logging_config.py': '''import logging

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
''',
'backend/app/db/base.py': '''from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
''',
'backend/app/db/session.py': '''from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models.file_insight import FileInsight
from app.models.repository import Repository, RepositoryRisk, RepositorySummary

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
'backend/app/models/__init__.py': '',
'backend/app/models/repository.py': '''from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repo_url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    primary_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    total_files_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    analysis_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    summary: Mapped["RepositorySummary"] = relationship(back_populates="repository", uselist=False, cascade="all, delete-orphan")
    risks: Mapped[list["RepositoryRisk"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    files: Mapped[list["FileInsight"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class RepositorySummary(Base):
    __tablename__ = "repository_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True)
    concise_summary: Mapped[str] = mapped_column(Text)
    detailed_summary: Mapped[str] = mapped_column(Text)
    architecture_summary: Mapped[str] = mapped_column(Text)
    onboarding_summary: Mapped[str] = mapped_column(Text)
    likely_stack: Mapped[list[str]] = mapped_column(JSON, default=list)
    repository: Mapped[Repository] = relationship(back_populates="summary")


class RepositoryRisk(Base):
    __tablename__ = "repository_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    repository: Mapped[Repository] = relationship(back_populates="risks")
''',
'backend/app/models/file_insight.py': '''from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileInsight(Base):
    __tablename__ = "file_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    path: Mapped[str] = mapped_column(String(500), index=True)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text)
    is_test_file: Mapped[bool] = mapped_column(Boolean, default=False)
    complexity_score: Mapped[int] = mapped_column(Integer, default=1)
    repository = relationship("Repository", back_populates="files")
''',
'backend/app/schemas/__init__.py': '',
'backend/app/schemas/chat.py': '''from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class ChatSource(BaseModel):
    file_path: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
''',
'backend/app/schemas/repository.py': '''from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: HttpUrl
    refresh: bool = False


class RepositorySummaryData(BaseModel):
    concise_summary: str
    detailed_summary: str
    architecture_summary: str
    onboarding_summary: str
    likely_stack: list[str]


class RepositoryRiskData(BaseModel):
    id: int
    title: str
    severity: str
    description: str
    file_path: str | None = None

    class Config:
        from_attributes = True


class FileInsightData(BaseModel):
    id: int
    path: str
    language: str | None = None
    size_bytes: int
    summary: str
    is_test_file: bool
    complexity_score: int

    class Config:
        from_attributes = True


class RepositoryDetailResponse(BaseModel):
    id: int
    repo_url: str
    owner: str
    name: str
    description: str | None = None
    default_branch: str
    stars: int
    forks: int
    open_issues: int
    primary_language: str | None = None
    language_breakdown: dict[str, int]
    total_files_analyzed: int
    analysis_duration_seconds: float


class AnalyzeRepositoryResponse(BaseModel):
    repository: RepositoryDetailResponse
    summary: RepositorySummaryData
    risks: list[RepositoryRiskData]
    files_preview: list[FileInsightData] = Field(default_factory=list)


class FileInsightListResponse(BaseModel):
    repo_id: int
    total: int
    files: list[FileInsightData]


class RepositorySummaryResponse(BaseModel):
    repo_id: int
    summary: RepositorySummaryData


class RiskListResponse(BaseModel):
    repo_id: int
    total: int
    risks: list[RepositoryRiskData]
''',
'backend/app/services/__init__.py': '',
'backend/app/services/github_service.py': '''from __future__ import annotations

import base64
import logging
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.utils.repository_filters import is_supported_source_file, infer_language_from_path

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self.client = httpx.Client(base_url=settings.github_api_base_url, headers=headers, timeout=30.0)

    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        parsed = urlparse(repo_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        return path_parts[0], path_parts[1].replace('.git', '')

    def get_repository_metadata(self, owner: str, repo: str) -> dict:
        response = self.client.get(f"/repos/{owner}/{repo}")
        self._raise_for_status(response)
        return response.json()

    def get_language_breakdown(self, owner: str, repo: str) -> dict[str, int]:
        response = self.client.get(f"/repos/{owner}/{repo}/languages")
        self._raise_for_status(response)
        return response.json()

    def get_repository_tree(self, owner: str, repo: str, branch: str) -> list[dict]:
        response = self.client.get(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        self._raise_for_status(response)
        data = response.json()
        return data.get("tree", [])

    def fetch_repository_files(self, owner: str, repo: str, branch: str) -> list[dict]:
        tree = self.get_repository_tree(owner, repo, branch)
        files: list[dict] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if not is_supported_source_file(path):
                continue
            if item.get("size", 0) > settings.max_file_bytes:
                continue
            files.append(
                {
                    "path": path,
                    "sha": item.get("sha"),
                    "size": item.get("size", 0),
                    "language": infer_language_from_path(path),
                }
            )
            if len(files) >= settings.max_files_to_analyze:
                break
        return files

    def get_file_content(self, owner: str, repo: str, path: str) -> str:
        response = self.client.get(f"/repos/{owner}/{repo}/contents/{path}")
        self._raise_for_status(response)
        data = response.json()
        encoded_content = data.get("content", "")
        if not encoded_content:
            return ""
        return base64.b64decode(encoded_content).decode("utf-8", errors="ignore")

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 403 and "rate limit" in response.text.lower():
            raise ValueError("GitHub API rate limit reached. Add a token or try again later.")
        if response.status_code == 404:
            raise ValueError("Repository or file not found. Check the URL and access level.")
        response.raise_for_status()
''',
'backend/app/services/analysis_service.py': '''from __future__ import annotations

import math
import re
from collections import Counter

from app.core.config import settings
from app.schemas.repository import RepositorySummaryData
from app.utils.repository_filters import infer_language_from_path

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "Possible OpenAI-style API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Possible AWS access key"),
    (re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{8,}"), "Hardcoded secret-like assignment"),
]


class AnalysisService:
    def summarize_file(self, path: str, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        first_lines = " ".join(lines[:3])[:220]
        language = infer_language_from_path(path) or "text"
        return f"{path} appears to be a {language} file. Preview: {first_lines or 'No meaningful content detected.'}"

    def estimate_complexity(self, content: str) -> int:
        control_flow_hits = len(re.findall(r"\b(if|for|while|switch|case|except|catch|elif)\b", content))
        nesting_penalty = content.count("{") + content.count(":\n")
        return min(10, max(1, math.ceil((control_flow_hits + nesting_penalty * 0.1) / 4)))

    def detect_risks(self, file_records: list[dict], repo_metadata: dict) -> list[dict]:
        risks: list[dict] = []
        has_readme = any(item["path"].lower().startswith("readme") for item in file_records)
        has_tests = any(item["is_test_file"] for item in file_records)

        if not has_readme:
            risks.append({"title": "Missing README", "severity": "medium", "description": "The repository does not include a visible README for onboarding.", "file_path": None})
        if not has_tests:
            risks.append({"title": "Missing tests", "severity": "medium", "description": "No test files were detected in the analyzed subset.", "file_path": None})

        for record in file_records:
            content = record["content"]
            path = record["path"]
            for pattern, description in SECRET_PATTERNS:
                if pattern.search(content):
                    risks.append({"title": "Potential hardcoded secret", "severity": "high", "description": description, "file_path": path})
                    break
            todo_count = len(re.findall(r"\b(TODO|FIXME|HACK)\b", content, flags=re.IGNORECASE))
            if todo_count >= 5:
                risks.append({"title": "High TODO/FIXME density", "severity": "low", "description": f"Detected {todo_count} TODO/FIXME markers, which may indicate unfinished work.", "file_path": path})
            if record["size"] > settings.max_file_bytes * 0.85:
                risks.append({"title": "Large source file", "severity": "medium", "description": "Large files can hurt maintainability and review speed.", "file_path": path})
            if record["complexity_score"] >= 8:
                risks.append({"title": "High complexity file", "severity": "medium", "description": "This file has high estimated branching complexity and may benefit from refactoring.", "file_path": path})

        if repo_metadata.get("open_issues_count", 0) > 50:
            risks.append({"title": "High open issue count", "severity": "low", "description": "A high issue count can indicate maintenance pressure.", "file_path": None})
        return risks[:20]

    def build_repo_summary(self, repo_metadata: dict, file_records: list[dict]) -> RepositorySummaryData:
        languages = Counter([record["language"] or "Unknown" for record in file_records])
        likely_stack = [language for language, _ in languages.most_common(5)]
        top_paths = ", ".join(record["path"] for record in file_records[:5])
        concise = (
            f"{repo_metadata['name']} is a GitHub repository owned by {repo_metadata['owner']['login']}. "
            f"The analyzed code suggests a {', '.join(likely_stack[:3]) or 'mixed-language'} project with {len(file_records)} source files reviewed."
        )
        detailed = (
            f"This repository likely focuses on {repo_metadata.get('description') or 'application or library development'}. "
            f"Primary languages include {', '.join(likely_stack) or 'unknown technologies'}. "
            f"Common entry points or notable files include {top_paths or 'no major files detected in the sampled set'}."
        )
        architecture = (
            "The platform appears to follow a modular repository layout based on the discovered directories and file naming. "
            "Core responsibilities seem split across UI, service, configuration, and test layers where present."
        )
        onboarding = (
            "Start by reading the README and package manifests, then inspect the main application entry points, API routes, and environment configuration. "
            "Run tests next to verify the local setup before making changes."
        )
        return RepositorySummaryData(
            concise_summary=concise,
            detailed_summary=detailed,
            architecture_summary=architecture,
            onboarding_summary=onboarding,
            likely_stack=likely_stack,
        )
''',
'backend/app/services/vector_store_service.py': '''from __future__ import annotations

from uuid import uuid4

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import settings


class VectorStoreService:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)

    def get_collection(self, repo_id: int) -> Collection:
        return self.client.get_or_create_collection(name=f"repo_{repo_id}")

    def upsert_chunks(self, repo_id: int, chunks: list[dict]) -> None:
        collection = self.get_collection(repo_id)
        ids = [str(uuid4()) for _ in chunks]
        collection.upsert(
            ids=ids,
            documents=[chunk["content"] for chunk in chunks],
            metadatas=[{"file_path": chunk["path"]} for chunk in chunks],
        )

    def search(self, repo_id: int, query: str, limit: int = 4) -> list[dict]:
        collection = self.get_collection(repo_id)
        results = collection.query(query_texts=[query], n_results=limit)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        return [
            {"content": doc, "file_path": metadata.get("file_path", "unknown")}
            for doc, metadata in zip(documents, metadatas, strict=False)
        ]
''',
'backend/app/services/llm_service.py': '''from __future__ import annotations

from app.schemas.chat import ChatResponse, ChatSource


class LLMService:
    """A lightweight abstraction layer.

    In production, swap the internals based on the selected provider.
    For a local interview demo, the fallback path keeps the app usable even without a paid model.
    """

    def answer_question(self, question: str, context_chunks: list[dict]) -> ChatResponse:
        if not context_chunks:
            return ChatResponse(answer="I could not find enough repository context to answer that question.", sources=[])
        bullet_points = []
        sources: list[ChatSource] = []
        for chunk in context_chunks[:3]:
            snippet = chunk["content"][:280].replace("\n", " ")
            bullet_points.append(f"- {chunk['file_path']}: {snippet}")
            sources.append(ChatSource(file_path=chunk["file_path"], snippet=snippet))
        answer = (
            f"Based on the indexed repository content, here is a grounded answer to '{question}':\n\n"
            + "\n".join(bullet_points)
            + "\n\nThe answer is synthesized from the most relevant repository chunks above."
        )
        return ChatResponse(answer=answer, sources=sources)
''',
'backend/app/services/repository_service.py': '''from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.file_insight import FileInsight
from app.models.repository import Repository, RepositoryRisk, RepositorySummary
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.repository import (
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    FileInsightData,
    FileInsightListResponse,
    RepositoryDetailResponse,
    RepositorySummaryData,
    RepositorySummaryResponse,
    RiskListResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.github_service import GitHubService
from app.services.llm_service import LLMService
from app.services.vector_store_service import VectorStoreService
from app.utils.chunking import chunk_text

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(self) -> None:
        self.github_service = GitHubService()
        self.analysis_service = AnalysisService()
        self.vector_store_service = VectorStoreService()
        self.llm_service = LLMService()

    def analyze_repository(self, db: Session, payload: AnalyzeRepositoryRequest) -> AnalyzeRepositoryResponse:
        owner, name = self.github_service.parse_repo_url(str(payload.repo_url))
        existing = db.scalar(select(Repository).where(Repository.repo_url == str(payload.repo_url)))
        if existing and not payload.refresh:
            return AnalyzeRepositoryResponse(
                repository=self._to_repository_detail(existing),
                summary=self._to_summary_data(existing.summary),
                risks=[RepositoryRiskData.model_validate(risk) for risk in existing.risks],
                files_preview=[FileInsightData.model_validate(file) for file in existing.files[:10]],
            )

        start_time = time.perf_counter()
        metadata = self.github_service.get_repository_metadata(owner, name)
        default_branch = metadata.get("default_branch", "main")
        language_breakdown = self.github_service.get_language_breakdown(owner, name)
        file_candidates = self.github_service.fetch_repository_files(owner, name, default_branch)

        file_records: list[dict[str, Any]] = []
        chunks: list[dict] = []
        for file_item in file_candidates:
            content = self.github_service.get_file_content(owner, name, file_item["path"])
            summary = self.analysis_service.summarize_file(file_item["path"], content)
            complexity_score = self.analysis_service.estimate_complexity(content)
            record = {
                **file_item,
                "content": content,
                "summary": summary,
                "is_test_file": any(part in file_item["path"].lower() for part in ["test", "spec"]),
                "complexity_score": complexity_score,
            }
            file_records.append(record)
            for chunk in chunk_text(content, chunk_size=1200, chunk_overlap=200):
                chunks.append({"path": file_item["path"], "content": chunk})

        repo_summary = self.analysis_service.build_repo_summary(metadata, file_records)
        repo_risks = self.analysis_service.detect_risks(file_records, metadata)
        duration = round(time.perf_counter() - start_time, 2)

        if existing:
            repository = existing
            db.execute(delete(RepositoryRisk).where(RepositoryRisk.repository_id == existing.id))
            db.execute(delete(FileInsight).where(FileInsight.repository_id == existing.id))
            if existing.summary:
                db.delete(existing.summary)
        else:
            repository = Repository(repo_url=str(payload.repo_url))
            db.add(repository)

        repository.owner = owner
        repository.name = name
        repository.description = metadata.get("description")
        repository.default_branch = default_branch
        repository.stars = metadata.get("stargazers_count", 0)
        repository.forks = metadata.get("forks_count", 0)
        repository.open_issues = metadata.get("open_issues_count", 0)
        repository.primary_language = metadata.get("language")
        repository.language_breakdown = language_breakdown
        repository.total_files_analyzed = len(file_records)
        repository.analysis_duration_seconds = duration
        db.flush()

        summary_model = RepositorySummary(
            repository_id=repository.id,
            concise_summary=repo_summary.concise_summary,
            detailed_summary=repo_summary.detailed_summary,
            architecture_summary=repo_summary.architecture_summary,
            onboarding_summary=repo_summary.onboarding_summary,
            likely_stack=repo_summary.likely_stack,
        )
        db.add(summary_model)

        for risk in repo_risks:
            db.add(RepositoryRisk(repository_id=repository.id, **risk))
        for record in file_records:
            db.add(
                FileInsight(
                    repository_id=repository.id,
                    path=record["path"],
                    language=record["language"],
                    size_bytes=record["size"],
                    summary=record["summary"],
                    is_test_file=record["is_test_file"],
                    complexity_score=record["complexity_score"],
                )
            )

        db.commit()
        db.refresh(repository)
        self.vector_store_service.upsert_chunks(repository.id, chunks[:500])
        repository = self._load_repository(db, repository.id)
        assert repository is not None
        return AnalyzeRepositoryResponse(
            repository=self._to_repository_detail(repository),
            summary=self._to_summary_data(repository.summary),
            risks=[RepositoryRiskData.model_validate(risk) for risk in repository.risks],
            files_preview=[FileInsightData.model_validate(file) for file in repository.files[:10]],
        )

    def get_repository(self, db: Session, repo_id: int) -> RepositoryDetailResponse | None:
        repository = self._load_repository(db, repo_id)
        if not repository:
            return None
        return self._to_repository_detail(repository)

    def get_file_insights(self, db: Session, repo_id: int) -> FileInsightListResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")
        return FileInsightListResponse(repo_id=repo_id, total=len(repository.files), files=[FileInsightData.model_validate(file) for file in repository.files])

    def get_summary(self, db: Session, repo_id: int) -> RepositorySummaryResponse | None:
        repository = self._load_repository(db, repo_id)
        if not repository or not repository.summary:
            return None
        return RepositorySummaryResponse(repo_id=repo_id, summary=self._to_summary_data(repository.summary))

    def get_risks(self, db: Session, repo_id: int) -> RiskListResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")
        return RiskListResponse(repo_id=repo_id, total=len(repository.risks), risks=[RepositoryRiskData.model_validate(risk) for risk in repository.risks])

    def chat(self, db: Session, repo_id: int, payload: ChatRequest) -> ChatResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")
        context_chunks = self.vector_store_service.search(repo_id, payload.question)
        return self.llm_service.answer_question(payload.question, context_chunks)

    def _load_repository(self, db: Session, repo_id: int) -> Repository | None:
        return db.scalar(
            select(Repository)
            .options(joinedload(Repository.summary), joinedload(Repository.risks), joinedload(Repository.files))
            .where(Repository.id == repo_id)
        )

    def _to_repository_detail(self, repository: Repository) -> RepositoryDetailResponse:
        return RepositoryDetailResponse(
            id=repository.id,
            repo_url=repository.repo_url,
            owner=repository.owner,
            name=repository.name,
            description=repository.description,
            default_branch=repository.default_branch,
            stars=repository.stars,
            forks=repository.forks,
            open_issues=repository.open_issues,
            primary_language=repository.primary_language,
            language_breakdown=repository.language_breakdown,
            total_files_analyzed=repository.total_files_analyzed,
            analysis_duration_seconds=repository.analysis_duration_seconds,
        )

    def _to_summary_data(self, summary: RepositorySummary | None) -> RepositorySummaryData:
        if not summary:
            return RepositorySummaryData(
                concise_summary="",
                detailed_summary="",
                architecture_summary="",
                onboarding_summary="",
                likely_stack=[],
            )
        return RepositorySummaryData(
            concise_summary=summary.concise_summary,
            detailed_summary=summary.detailed_summary,
            architecture_summary=summary.architecture_summary,
            onboarding_summary=summary.onboarding_summary,
            likely_stack=summary.likely_stack,
        )


from app.schemas.repository import RepositoryRiskData  # noqa: E402
''',
'backend/app/utils/__init__.py': '',
'backend/app/utils/repository_filters.py': '''from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".jsx": "JSX",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
}
IGNORED_PARTS = {"node_modules", "dist", "build", ".next", ".git", "coverage", "venv", ".venv"}
IGNORED_FILENAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}


def infer_language_from_path(path: str) -> str | None:
    return SUPPORTED_EXTENSIONS.get(Path(path).suffix.lower())


def is_supported_source_file(path: str) -> bool:
    parts = set(Path(path).parts)
    filename = Path(path).name
    if parts.intersection(IGNORED_PARTS):
        return False
    if filename in IGNORED_FILENAMES:
        return False
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS
''',
'backend/app/utils/chunking.py': '''def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> list[str]:
    if not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks
''',
'backend/tests/test_chunking.py': '''from app.utils.chunking import chunk_text


def test_chunk_text_splits_large_input() -> None:
    text = "a" * 3000
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)
    assert len(chunks) >= 3
    assert chunks[0] == "a" * 1000
''',
'backend/tests/test_filters.py': '''from app.utils.repository_filters import infer_language_from_path, is_supported_source_file


def test_infer_language_from_path() -> None:
    assert infer_language_from_path("src/main.py") == "Python"


def test_ignore_node_modules() -> None:
    assert is_supported_source_file("node_modules/react/index.js") is False
''',
'frontend/package.json': '''{
  "name": "codelens-ai-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.11.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.30.1",
    "recharts": "^2.15.4"
  },
  "devDependencies": {
    "@types/react": "^18.3.23",
    "@types/react-dom": "^18.3.7",
    "@vitejs/plugin-react": "^5.0.0",
    "autoprefixer": "^10.4.21",
    "postcss": "^8.5.6",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.9.2",
    "vite": "^7.1.3"
  }
}
''',
'frontend/index.html': '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CodeLens AI</title>
  </head>
  <body class="bg-slate-950">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
''',
'frontend/tsconfig.json': '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
''',
'frontend/vite.config.ts': '''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
''',
'frontend/postcss.config.js': '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
''',
'frontend/tailwind.config.js': '''/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
''',
'frontend/src/index.css': '''@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-slate-950 text-slate-100 antialiased;
  font-family: Inter, system-ui, sans-serif;
}

.card {
  @apply rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg;
}
''',
'frontend/src/main.tsx': '''import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
''',
'frontend/src/App.tsx': '''import { Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/repo/:repoId" element={<DashboardPage />} />
    </Routes>
  );
}
''',
'frontend/src/types/index.ts': '''export interface RepositoryDetail {
  id: number;
  repo_url: string;
  owner: string;
  name: string;
  description?: string;
  default_branch: string;
  stars: number;
  forks: number;
  open_issues: number;
  primary_language?: string;
  language_breakdown: Record<string, number>;
  total_files_analyzed: number;
  analysis_duration_seconds: number;
}

export interface RepositorySummary {
  concise_summary: string;
  detailed_summary: string;
  architecture_summary: string;
  onboarding_summary: string;
  likely_stack: string[];
}

export interface RepositoryRisk {
  id: number;
  title: string;
  severity: "low" | "medium" | "high" | string;
  description: string;
  file_path?: string;
}

export interface FileInsight {
  id: number;
  path: string;
  language?: string;
  size_bytes: number;
  summary: string;
  is_test_file: boolean;
  complexity_score: number;
}

export interface AnalyzeResponse {
  repository: RepositoryDetail;
  summary: RepositorySummary;
  risks: RepositoryRisk[];
  files_preview: FileInsight[];
}

export interface ChatSource {
  file_path: string;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}
''',
'frontend/src/services/api.ts': '''import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 60000,
});
''',
'frontend/src/services/repositoryService.ts': '''import { api } from "./api";
import { AnalyzeResponse, ChatResponse, FileInsight, RepositoryDetail, RepositoryRisk, RepositorySummary } from "../types";

export async function analyzeRepository(repoUrl: string): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>("/analyze", { repo_url: repoUrl });
  return data;
}

export async function getRepository(repoId: string): Promise<RepositoryDetail> {
  const { data } = await api.get<RepositoryDetail>(`/repo/${repoId}`);
  return data;
}

export async function getRepositoryFiles(repoId: string): Promise<{ repo_id: number; total: number; files: FileInsight[] }> {
  const { data } = await api.get(`/repo/${repoId}/files`);
  return data;
}

export async function getRepositorySummary(repoId: string): Promise<{ repo_id: number; summary: RepositorySummary }> {
  const { data } = await api.get(`/repo/${repoId}/summary`);
  return data;
}

export async function getRepositoryRisks(repoId: string): Promise<{ repo_id: number; total: number; risks: RepositoryRisk[] }> {
  const { data } = await api.get(`/repo/${repoId}/risks`);
  return data;
}

export async function askRepositoryQuestion(repoId: string, question: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>(`/repo/${repoId}/chat`, { question });
  return data;
}
''',
'frontend/src/components/RepoInputForm.tsx': '''import { FormEvent, useState } from "react";

interface Props {
  onSubmit: (repoUrl: string) => Promise<void>;
  loading: boolean;
}

export default function RepoInputForm({ onSubmit, loading }: Props) {
  const [repoUrl, setRepoUrl] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onSubmit(repoUrl);
  };

  return (
    <form onSubmit={handleSubmit} className="card p-6">
      <label className="mb-3 block text-sm font-medium text-slate-300">GitHub Repository URL</label>
      <div className="flex flex-col gap-3 md:flex-row">
        <input
          type="url"
          required
          value={repoUrl}
          onChange={(event) => setRepoUrl(event.target.value)}
          placeholder="https://github.com/owner/repository"
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none ring-0 placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Analyzing..." : "Analyze Repository"}
        </button>
      </div>
      <p className="mt-3 text-sm text-slate-400">Public repositories work out of the box. Add a GitHub token in the backend for better rate limits.</p>
    </form>
  );
}
''',
'frontend/src/components/SummaryCards.tsx': '''import { RepositoryDetail, RepositorySummary } from "../types";

interface Props {
  repository: RepositoryDetail;
  summary: RepositorySummary;
}

export default function SummaryCards({ repository, summary }: Props) {
  const stats = [
    { label: "Stars", value: repository.stars },
    { label: "Forks", value: repository.forks },
    { label: "Open Issues", value: repository.open_issues },
    { label: "Files Analyzed", value: repository.total_files_analyzed },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((item) => (
          <div key={item.label} className="card p-5">
            <p className="text-sm text-slate-400">{item.label}</p>
            <p className="mt-2 text-3xl font-bold">{item.value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <h3 className="text-lg font-semibold">Concise Summary</h3>
          <p className="mt-3 text-slate-300">{summary.concise_summary}</p>
        </div>
        <div className="card p-6">
          <h3 className="text-lg font-semibold">Architecture Summary</h3>
          <p className="mt-3 text-slate-300">{summary.architecture_summary}</p>
        </div>
      </div>
    </div>
  );
}
''',
'frontend/src/components/LanguageChart.tsx': '''import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  languageBreakdown: Record<string, number>;
}

const colors = ["#06b6d4", "#8b5cf6", "#14b8a6", "#f59e0b", "#ef4444", "#64748b"];

export default function LanguageChart({ languageBreakdown }: Props) {
  const data = Object.entries(languageBreakdown).map(([name, value]) => ({ name, value }));

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold">Language Distribution</h3>
      <div className="mt-4 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={100} label>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
''',
'frontend/src/components/FileInsightsPanel.tsx': '''import { FileInsight } from "../types";

interface Props {
  files: FileInsight[];
}

export default function FileInsightsPanel({ files }: Props) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">File Insights</h3>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{files.length} files</span>
      </div>
      <div className="mt-4 space-y-3">
        {files.map((file) => (
          <div key={file.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium text-cyan-300">{file.path}</p>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{file.language || "Unknown"}</span>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">Complexity {file.complexity_score}/10</span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{file.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
''',
'frontend/src/components/RiskPanel.tsx': '''import { RepositoryRisk } from "../types";

interface Props {
  risks: RepositoryRisk[];
}

const severityClasses: Record<string, string> = {
  low: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  medium: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  high: "bg-rose-500/10 text-rose-300 border-rose-500/30",
};

export default function RiskPanel({ risks }: Props) {
  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold">Security & Quality Findings</h3>
      <div className="mt-4 space-y-3">
        {risks.length === 0 ? (
          <p className="text-slate-400">No major risks detected in the current analysis snapshot.</p>
        ) : (
          risks.map((risk) => (
            <div key={risk.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{risk.title}</p>
                <span className={`rounded-full border px-3 py-1 text-xs font-medium ${severityClasses[risk.severity] || severityClasses.low}`}>
                  {risk.severity}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-400">{risk.description}</p>
              {risk.file_path ? <p className="mt-2 text-xs text-slate-500">File: {risk.file_path}</p> : null}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
''',
'frontend/src/components/ChatPanel.tsx': '''import { FormEvent, useState } from "react";
import { ChatResponse } from "../types";

interface Props {
  onAsk: (question: string) => Promise<ChatResponse>;
}

export default function ChatPanel({ onAsk }: Props) {
  const [question, setQuestion] = useState("Where is authentication implemented?");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await onAsk(question);
      setResponse(result);
    } catch (err) {
      setError("Unable to get an answer right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold">Repository Chat</h3>
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          className="min-h-28 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100"
        />
        <button type="submit" disabled={loading} className="rounded-xl bg-violet-500 px-4 py-2 font-semibold text-white disabled:opacity-60">
          {loading ? "Thinking..." : "Ask"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      {response ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 whitespace-pre-wrap text-sm text-slate-300">{response.answer}</div>
          <div>
            <p className="text-sm font-medium text-slate-200">Sources</p>
            <div className="mt-2 space-y-2">
              {response.sources.map((source) => (
                <div key={`${source.file_path}-${source.snippet.slice(0, 30)}`} className="rounded-xl border border-slate-800 p-3 text-sm">
                  <p className="font-medium text-cyan-300">{source.file_path}</p>
                  <p className="mt-1 text-slate-400">{source.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
''',
'frontend/src/pages/LandingPage.tsx': '''import { useState } from "react";
import { useNavigate } from "react-router-dom";
import RepoInputForm from "../components/RepoInputForm";
import { analyzeRepository } from "../services/repositoryService";

export default function LandingPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAnalyze = async (repoUrl: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRepository(repoUrl);
      navigate(`/repo/${result.repository.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Repository analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-16">
      <section className="grid gap-10 lg:grid-cols-[1.2fr,0.8fr] lg:items-center">
        <div>
          <p className="inline-flex rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-sm text-cyan-300">
            AI-powered repository analysis for interview demos
          </p>
          <h1 className="mt-6 text-5xl font-bold tracking-tight">CodeLens AI</h1>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Paste a public GitHub repository URL and get metadata, file insights, risk detection, AI summaries, and a grounded repository chatbot in one dashboard.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {[
              "Repository metadata and codebase structure",
              "Language breakdown and file explorer",
              "Security and code-quality findings",
              "RAG-style chat grounded in repository content",
            ].map((feature) => (
              <div key={feature} className="card p-4 text-slate-300">{feature}</div>
            ))}
          </div>
        </div>
        <div>
          <RepoInputForm onSubmit={handleAnalyze} loading={loading} />
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}
''',
'frontend/src/pages/DashboardPage.tsx': '''import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import FileInsightsPanel from "../components/FileInsightsPanel";
import LanguageChart from "../components/LanguageChart";
import RiskPanel from "../components/RiskPanel";
import SummaryCards from "../components/SummaryCards";
import { askRepositoryQuestion, getRepository, getRepositoryFiles, getRepositoryRisks, getRepositorySummary } from "../services/repositoryService";
import { ChatResponse, FileInsight, RepositoryDetail, RepositoryRisk, RepositorySummary } from "../types";

export default function DashboardPage() {
  const { repoId = "" } = useParams();
  const [repository, setRepository] = useState<RepositoryDetail | null>(null);
  const [summary, setSummary] = useState<RepositorySummary | null>(null);
  const [files, setFiles] = useState<FileInsight[]>([]);
  const [risks, setRisks] = useState<RepositoryRisk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [repoData, summaryData, filesData, risksData] = await Promise.all([
          getRepository(repoId),
          getRepositorySummary(repoId),
          getRepositoryFiles(repoId),
          getRepositoryRisks(repoId),
        ]);
        setRepository(repoData);
        setSummary(summaryData.summary);
        setFiles(filesData.files);
        setRisks(risksData.risks);
      } catch (err) {
        setError("Unable to load repository dashboard.");
      } finally {
        setLoading(false);
      }
    }

    void loadDashboard();
  }, [repoId]);

  const handleAsk = async (question: string): Promise<ChatResponse> => askRepositoryQuestion(repoId, question);

  if (loading) {
    return <main className="mx-auto max-w-6xl px-6 py-16 text-slate-300">Loading dashboard...</main>;
  }
  if (error || !repository || !summary) {
    return <main className="mx-auto max-w-6xl px-6 py-16 text-rose-300">{error || "Repository not found."}</main>;
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/" className="text-sm text-cyan-300 hover:text-cyan-200">← Analyze another repository</Link>
          <h1 className="mt-2 text-4xl font-bold">{repository.owner}/{repository.name}</h1>
          <p className="mt-2 max-w-3xl text-slate-400">{repository.description || "No description provided."}</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-300">
          Completed in {repository.analysis_duration_seconds}s
        </div>
      </div>

      <SummaryCards repository={repository} summary={summary} />

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr,1fr]">
        <LanguageChart languageBreakdown={repository.language_breakdown} />
        <RiskPanel risks={risks} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <FileInsightsPanel files={files} />
        <ChatPanel onAsk={handleAsk} />
      </div>

      <div className="mt-6 card p-6">
        <h3 className="text-lg font-semibold">Detailed Summary</h3>
        <p className="mt-3 text-slate-300">{summary.detailed_summary}</p>
        <h4 className="mt-5 text-base font-semibold">Developer Onboarding</h4>
        <p className="mt-2 text-slate-400">{summary.onboarding_summary}</p>
      </div>
    </main>
  );
}
''',
'frontend/.env.example': '''VITE_API_BASE_URL=http://localhost:8000/api/v1
''',
'README.md': '''# CodeLens AI

CodeLens AI is a production-style full-stack GitHub repository analysis platform built for interview presentations. A user can paste a public GitHub repository URL and get repository metadata, codebase analysis, language breakdown, file-level insights, AI-generated summaries, security/code-quality findings, and a grounded repository chat experience.

## Why this project is strong for interviews

- Shows full-stack engineering with React + TypeScript + FastAPI
- Demonstrates practical AI usage with retrieval-style repository chat
- Highlights engineering tradeoffs around GitHub API rate limits, chunking, and analysis scope
- Uses modular architecture, tests, environment-based config, and good developer experience

## Folder structure

```text
codelens_ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── .env.example
│   └── package.json
└── README.md
```

## Backend API

- `POST /api/v1/analyze`
- `GET /api/v1/repo/{repo_id}`
- `GET /api/v1/repo/{repo_id}/files`
- `GET /api/v1/repo/{repo_id}/summary`
- `GET /api/v1/repo/{repo_id}/risks`
- `POST /api/v1/repo/{repo_id}/chat`
- `GET /api/v1/health`

## Architecture and design decisions

### Why FastAPI
FastAPI is a strong choice for interview-quality Python backends because it offers clean request validation with Pydantic, automatic docs, async-ready performance, and readable code.

### Why RAG-style chat
Instead of asking an LLM to guess based on repository metadata, the app indexes repository chunks into a vector store and retrieves the most relevant snippets first. That makes answers more grounded and explainable.

### Why chunk repository files
Repositories contain long source files. Chunking keeps retrieval focused, reduces noisy context, and lets the system cite the file paths that informed the answer.

### Why a vector database
A vector store makes semantic search over code and docs practical. For a demo, ChromaDB is lightweight and easy to run locally.

### Tradeoffs made
- The app limits file count and file size for speed and predictable demo performance.
- It ignores binaries and build outputs to keep retrieval quality high.
- The current LLM service includes a fallback synthesized answer path so the demo still works without a paid API key.

## Local setup

### 1) Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### 2) Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### 3) Open the app

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Environment variables

### Backend
- `GITHUB_TOKEN`: recommended for higher GitHub API rate limits
- `OPENAI_API_KEY`: optional for future provider-backed responses
- `LLM_PROVIDER`: abstraction switch for future OpenAI/Ollama/Groq/OpenRouter support

### Frontend
- `VITE_API_BASE_URL`: backend base URL

## Tests

```bash
cd backend
pytest -q
```

## Suggested demo flow for interview presentation

1. Start on the landing page and explain the problem: onboarding to unfamiliar repositories is slow.
2. Paste a public GitHub repo URL and run analysis.
3. Walk through metadata, language distribution, and file insights.
4. Show the security/code-quality findings panel.
5. Ask the chat a grounded question like: “Where is authentication implemented?”
6. Explain chunking, vector search, and why responses cite source files.
7. Close with tradeoffs and production improvements.

## Possible future improvements

- Background jobs for large repository analysis
- True provider abstraction with OpenAI, Ollama, Groq, and OpenRouter implementations
- Redis caching for repeated repo analyses
- User authentication and saved analyses
- Better static analysis with AST parsing and secret scanning libraries
- Streaming chat responses
- Async GitHub fetching and batching for faster large-repo performance
- Better ranking for retrieval and hybrid search over code + metadata

## Notes for your interview

Use these talking points:
- I chose FastAPI for typed APIs, clean structure, and speed of development.
- I used retrieval-based chat so answers are grounded in repository content instead of being generic.
- I chunk repository files to balance context quality and response speed.
- I capped analysis size to keep the MVP fast and predictable, which is a practical engineering tradeoff.
- For production, I would move analysis to async jobs, add caching, and support larger repos with pagination and smarter filtering.
'''
}

for rel, content in files.items():
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


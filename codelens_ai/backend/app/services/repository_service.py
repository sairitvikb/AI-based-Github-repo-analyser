from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.file_insight import FileInsight
from app.models.improvement import RepositoryImprovement
from app.models.repository import Repository, RepositoryRisk, RepositorySummary
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.improvement import ImprovementListResponse
from app.schemas.repository import (
    AnalyzeRepositoryRequest,
    AnalyzeRepositoryResponse,
    FileInsightData,
    FileInsightListResponse,
    RepositoryDetailResponse,
    RepositoryRiskData,
    RepositorySummaryData,
    RepositorySummaryResponse,
    RiskListResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.github_service import GitHubService
from app.services.llm_service import LLMService
from app.services.vector_store_service import VectorStoreService
from app.utils.chunking import chunk_text
from app.utils.repository_filters import get_file_priority, is_low_signal_file

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

        ranked_candidates = sorted(
            file_candidates,
            key=lambda item: (get_file_priority(item["path"]), -item["size"]),
            reverse=True,
        )

        max_files = settings.max_files_to_analyze
        selected_candidates = ranked_candidates[:max_files]

        file_records: list[dict[str, Any]] = []
        chunks: list[dict[str, Any]] = []

        for file_item in selected_candidates:
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

            if is_low_signal_file(file_item["path"]):
                continue

            for chunk in chunk_text(
                content,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            ):
                chunks.append(
                    {
                        "path": file_item["path"],
                        "content": chunk,
                        "priority": get_file_priority(file_item["path"]),
                    }
                )

        chunks = sorted(chunks, key=lambda item: item["priority"], reverse=True)[:300]

        repo_summary = self.analysis_service.build_repo_summary(metadata, file_records)
        repo_risks = self.analysis_service.detect_risks(file_records, metadata)
        repo_improvements = self.analysis_service.suggest_improvements(file_records, metadata)
        duration = round(time.perf_counter() - start_time, 2)

        if existing:
            repository = existing
            db.execute(delete(RepositoryRisk).where(RepositoryRisk.repository_id == existing.id))
            db.execute(delete(FileInsight).where(FileInsight.repository_id == existing.id))
            db.execute(delete(RepositoryImprovement).where(RepositoryImprovement.repository_id == existing.id))
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

        for improvement in repo_improvements:
            db.add(RepositoryImprovement(repository_id=repository.id, **improvement))

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

        self.vector_store_service.reset_collection(repository.id)
        self.vector_store_service.upsert_chunks(repository.id, chunks)

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
        return FileInsightListResponse(
            repo_id=repo_id,
            total=len(repository.files),
            files=[FileInsightData.model_validate(file) for file in repository.files],
        )

    def get_summary(self, db: Session, repo_id: int) -> RepositorySummaryResponse | None:
        repository = self._load_repository(db, repo_id)
        if not repository or not repository.summary:
            return None
        return RepositorySummaryResponse(repo_id=repo_id, summary=self._to_summary_data(repository.summary))

    def get_risks(self, db: Session, repo_id: int) -> RiskListResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")
        return RiskListResponse(
            repo_id=repo_id,
            total=len(repository.risks),
            risks=[RepositoryRiskData.model_validate(risk) for risk in repository.risks],
        )

    def get_improvements(self, db: Session, repo_id: int) -> ImprovementListResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")

        return ImprovementListResponse(
            repo_id=repo_id,
            total=len(repository.improvements),
            improvements=[
                {
                    "title": item.title,
                    "category": item.category,
                    "priority": item.priority,
                    "description": item.description,
                    "rationale": item.rationale,
                }
                for item in repository.improvements
            ],
        )

    def chat(self, db: Session, repo_id: int, payload: ChatRequest) -> ChatResponse:
        repository = self._load_repository(db, repo_id)
        if not repository:
            raise ValueError("Repository not found")
        context_chunks = self.vector_store_service.search(repo_id, payload.question)
        return self.llm_service.answer_question(payload.question, context_chunks)

    def _load_repository(self, db: Session, repo_id: int) -> Repository | None:
        return db.scalar(
            select(Repository)
            .options(
                joinedload(Repository.summary),
                joinedload(Repository.risks),
                joinedload(Repository.files),
                joinedload(Repository.improvements),
            )
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
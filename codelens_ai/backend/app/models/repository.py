from datetime import datetime

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

    summary: Mapped["RepositorySummary"] = relationship(
        back_populates="repository",
        uselist=False,
        cascade="all, delete-orphan",
    )
    risks: Mapped[list["RepositoryRisk"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["FileInsight"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    improvements: Mapped[list["RepositoryImprovement"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )


class RepositorySummary(Base):
    __tablename__ = "repository_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True)
    concise_summary: Mapped[str] = mapped_column(Text)
    detailed_summary: Mapped[str] = mapped_column(Text)
    architecture_summary: Mapped[str] = mapped_column(Text)
    onboarding_summary: Mapped[str] = mapped_column(Text)
    likely_stack: Mapped[list[str]] = mapped_column(JSON, default=list)

    repository: Mapped["Repository"] = relationship(back_populates="summary")


class RepositoryRisk(Base):
    __tablename__ = "repository_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="risks")
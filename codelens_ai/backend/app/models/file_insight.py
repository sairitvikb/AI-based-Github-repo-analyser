from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
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

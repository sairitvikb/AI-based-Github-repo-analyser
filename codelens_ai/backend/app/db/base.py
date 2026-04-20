from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models AFTER Base is created
from app.models.repository import Repository, RepositoryRisk, RepositorySummary
from app.models.file_insight import FileInsight
from app.models.improvement import RepositoryImprovement
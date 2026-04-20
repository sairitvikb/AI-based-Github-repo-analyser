from pydantic import BaseModel, Field, HttpUrl


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

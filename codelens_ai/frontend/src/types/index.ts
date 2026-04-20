export interface RepositoryDetail {
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

export interface ImprovementItem {
  title: string;
  category: string;
  priority: string;
  description: string;
  rationale: string;
}

export interface ImprovementListResponse {
  repo_id: number;
  total: number;
  improvements: ImprovementItem[];
}
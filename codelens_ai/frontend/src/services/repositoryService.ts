import { api } from "./api";
import { AnalyzeResponse, ChatResponse, FileInsight, ImprovementListResponse, RepositoryDetail, RepositoryRisk, RepositorySummary } from "../types";

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

export async function getImprovements(repoId: string) {
  const response = await api.get<ImprovementListResponse>(`/repo/${repoId}/improvements`);
  return response.data;
}

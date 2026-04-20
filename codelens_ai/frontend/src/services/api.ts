import axios from "axios";
import type { ImprovementListResponse } from "../types/improvement";

export const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1`,
  timeout: 60000,
});

export const getImprovements = async (
  repoId: number
): Promise<ImprovementListResponse> => {
  const response = await api.get(`/repo/${repoId}/improvements`);
  return response.data;
};

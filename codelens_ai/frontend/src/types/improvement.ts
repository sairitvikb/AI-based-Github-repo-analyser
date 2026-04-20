// frontend/src/types/improvement.ts

export type ImprovementItem = {
  title: string;
  category: string;
  priority: "High" | "Medium" | "Low" | string;
  description: string;
  rationale: string;
};

export type ImprovementListResponse = {
  repo_id: number;
  total: number;
  improvements: ImprovementItem[];
};
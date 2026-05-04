import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import FileInsightsPanel from "../components/FileInsightsPanel";
import ImprovementOpportunities from "../components/ImprovementOpportunities";
import LanguageChart from "../components/LanguageChart";
import RiskPanel from "../components/RiskPanel";
import SummaryCards from "../components/SummaryCards";
import {
  askRepositoryQuestion,
  getImprovements,
  getRepository,
  getRepositoryFiles,
  getRepositoryRisks,
  getRepositorySummary,
} from "../services/repositoryService";
import {
  ChatResponse,
  FileInsight,
  ImprovementItem,
  RepositoryDetail,
  RepositoryRisk,
  RepositorySummary,
} from "../types";

export default function DashboardPage() {
  const { repoId = "" } = useParams();

  const [repository, setRepository] = useState<RepositoryDetail | null>(null);
  const [summary, setSummary] = useState<RepositorySummary | null>(null);
  const [files, setFiles] = useState<FileInsight[]>([]);
  const [risks, setRisks] = useState<RepositoryRisk[]>([]);
  const [improvements, setImprovements] = useState<ImprovementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        setError(null);

        const [repoData, summaryData, filesData, risksData, improvementsData] = await Promise.all([
          getRepository(repoId),
          getRepositorySummary(repoId),
          getRepositoryFiles(repoId),
          getRepositoryRisks(repoId),
          getImprovements(repoId),
        ]);

        setRepository(repoData);
        setSummary(summaryData.summary);
        setFiles(filesData.files);
        setRisks(risksData.risks);
        setImprovements(improvementsData.improvements);
      } catch (err) {
        setError("Unable to load repository dashboard.");
      } finally {
        setLoading(false);
      }
    }

    if (repoId) {
      void loadDashboard();
    }
  }, [repoId]);

  const handleAsk = async (question: string): Promise<ChatResponse> => {
    return askRepositoryQuestion(repoId, question);
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-16 text-slate-300">
        Loading dashboard...
      </main>
    );
  }

  if (error || !repository || !summary) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-16 text-rose-300">
        {error || "Repository not found."}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/" className="text-sm text-cyan-300 hover:text-cyan-200">
            ← Analyze another repository
          </Link>
          <h1 className="mt-2 text-4xl font-bold">
            {repository.owner}/{repository.name}
          </h1>
          <p className="mt-2 max-w-3xl text-slate-400">
            {repository.description || "No description provided."}
          </p>
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

      <div className="mt-6">
        <ImprovementOpportunities improvements={improvements} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <FileInsightsPanel files={files} />
        <ChatPanel onAsk={handleAsk} />
      </div>

      <div className="mt-6 card p-6">
        <h3 className="text-lg font-semibold">Detailed Summary</h3>
        <p className="mt-3 text-slate-300">{summary.detailed_summary}</p>

        <h4 className="mt-5 text-base font-semibold">Developer Onboarding</h4>
        <p className="mt-3 text-slate-300">{summary.onboarding_summary}</p>
      </div>
    </main>
  );
}

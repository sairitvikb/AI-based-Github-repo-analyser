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

        const [
          repoData,
          summaryData,
          filesData,
          risksData,
          improvementsData,
        ] = await Promise.all([
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
      {/* Header */}
      <section className="mb-8 rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link to="/" className="text-sm text-cyan-300 hover:text-cyan-200">
              ← Analyze another repository
            </Link>

            <h1 className="mt-3 text-4xl font-bold text-white">
              {repository.owner}/{repository.name}
            </h1>

            <p className="mt-3 max-w-3xl text-slate-400 leading-relaxed">
              {repository.description || "No description provided."}
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-5 py-4 text-sm text-cyan-200">
            Completed in{" "}
            <span className="font-semibold text-white">
              {repository.analysis_duration_seconds}s
            </span>
          </div>
        </div>
      </section>

      <SummaryCards repository={repository} summary={summary} />

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
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

      {/* Detailed Text Sections */}
      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-7 shadow-lg transition hover:-translate-y-1 hover:border-cyan-400/40 hover:shadow-cyan-500/10">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-400/10 text-xl">
              🧠
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">
                Detailed Summary
              </h3>
              <p className="text-sm text-slate-400">
                Full AI-generated understanding of the repository.
              </p>
            </div>
          </div>

          <p className="text-slate-300 leading-8">
            {summary.detailed_summary}
          </p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-7 shadow-lg transition hover:-translate-y-1 hover:border-indigo-400/40 hover:shadow-indigo-500/10">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-400/10 text-xl">
              🚀
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white">
                Developer Onboarding
              </h3>
              <p className="text-sm text-slate-400">
                How a new developer can quickly understand this codebase.
              </p>
            </div>
          </div>

          <p className="text-slate-300 leading-8">
            {summary.onboarding_summary}
          </p>
        </div>
      </section>
    </main>
  );
}

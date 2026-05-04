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
  const [activeSection, setActiveSection] = useState("overview");
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);

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

  const scrollToSection = (sectionId: string) => {
    setActiveSection(sectionId);
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  const handleRiskFileSelect = (filePath: string) => {
    setSelectedFilePath(filePath);
    setActiveSection("files");

    setTimeout(() => {
      document.getElementById("files")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 50);
  };

  if (loading) {
    return (
      <main className="relative mx-auto max-w-7xl px-6 py-16 text-slate-300">
        <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.14),transparent_35%),radial-gradient(circle_at_top_right,rgba(99,102,241,0.14),transparent_35%)]" />

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-8">
          <div className="mb-4 h-7 w-64 animate-pulse rounded bg-slate-800" />
          <div className="mb-3 h-4 w-full max-w-3xl animate-pulse rounded bg-slate-800" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-800" />
          <p className="mt-6 text-cyan-300">Loading dashboard...</p>
        </div>
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
    <main className="relative mx-auto max-w-7xl px-6 py-10">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.14),transparent_35%),radial-gradient(circle_at_top_right,rgba(99,102,241,0.14),transparent_35%)]" />

      <section className="mb-8 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl transition hover:border-cyan-400/30">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Link
              to="/"
              className="inline-flex items-center rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-300 transition hover:bg-cyan-400/20 hover:text-cyan-100"
            >
              ← Analyze another repository
            </Link>

            <h1 className="mt-5 text-4xl font-bold text-white">
              {repository.owner}/{repository.name}
            </h1>

            <p className="mt-3 max-w-3xl text-slate-400 leading-relaxed">
              {repository.description || "No description provided."}
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <span className="rounded-full border border-slate-700 bg-slate-950/60 px-4 py-2 text-sm text-slate-300">
                AI Repository Analysis
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-950/60 px-4 py-2 text-sm text-slate-300">
                File Insights
              </span>
              <span className="rounded-full border border-slate-700 bg-slate-950/60 px-4 py-2 text-sm text-slate-300">
                Risk Detection
              </span>
            </div>
          </div>

          <div className="rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-6 text-center">
            <p className="text-sm text-cyan-200">Analysis Time</p>
            <p className="mt-2 text-3xl font-bold text-white">
              {repository.analysis_duration_seconds}s
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Completed successfully
            </p>
          </div>
        </div>
      </section>

      <nav className="sticky top-4 z-20 mb-8 rounded-2xl border border-slate-800 bg-slate-950/80 p-2 backdrop-blur">
        <div className="flex flex-wrap gap-2">
          {[
            { id: "overview", label: "Overview" },
            { id: "risks", label: "Risks" },
            { id: "improvements", label: "Improvements" },
            { id: "files", label: "Files & Chat" },
            { id: "summary", label: "Deep Summary" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => scrollToSection(tab.id)}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                activeSection === tab.id
                  ? "bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/20"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <section id="overview" className="scroll-mt-28">
        <SummaryCards repository={repository} summary={summary} />
      </section>

      <section id="risks" className="mt-6 grid scroll-mt-28 gap-6 xl:grid-cols-2">
        <div className="transition duration-300 hover:-translate-y-1">
          <LanguageChart languageBreakdown={repository.language_breakdown} />
        </div>

        <div className="transition duration-300 hover:-translate-y-1">
          <RiskPanel risks={risks} onFileSelect={handleRiskFileSelect} />
        </div>
      </section>

      <section
        id="improvements"
        className="mt-6 scroll-mt-28 transition duration-300 hover:-translate-y-1"
      >
        <ImprovementOpportunities improvements={improvements} />
      </section>

      <section
        id="files"
        className="mt-6 grid scroll-mt-28 gap-6 xl:grid-cols-[1.1fr,0.9fr]"
      >
        <div className="transition duration-300 hover:-translate-y-1">
          <FileInsightsPanel
            files={files}
            selectedFilePath={selectedFilePath}
          />
        </div>

        <div className="transition duration-300 hover:-translate-y-1">
          <ChatPanel onAsk={handleAsk} />
        </div>
      </section>

      <section id="summary" className="mt-6 grid scroll-mt-28 gap-6 lg:grid-cols-2">
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

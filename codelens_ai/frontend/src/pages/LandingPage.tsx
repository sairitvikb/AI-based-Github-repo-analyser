import { useState } from "react";
import { useNavigate } from "react-router-dom";
import RepoInputForm from "../components/RepoInputForm";
import { analyzeRepository } from "../services/repositoryService";

export default function LandingPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAnalyze = async (repoUrl: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeRepository(repoUrl);
      navigate(`/repo/${result.repository.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Repository analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-16">
      <section className="grid gap-10 lg:grid-cols-[1.2fr,0.8fr] lg:items-center">
        <div>
          <p className="inline-flex rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-sm text-cyan-300">
            AI-powered GitHub repository analysis  
          </p>
          <h1 className="mt-6 text-5xl font-bold tracking-tight">Codelens.ai</h1>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Paste a public GitHub repository URL and get metadata, file insights, risk detection, AI summaries, and a grounded repository chatbot in one dashboard.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {[
              "Repository metadata and codebase structure",
              "Language breakdown and file explorer",
              "Security and code-quality findings",
              "RAG-style chat grounded in repository content",
            ].map((feature) => (
              <div key={feature} className="card p-4 text-slate-300">{feature}</div>
            ))}
          </div>
        </div>
        <div>
          <RepoInputForm onSubmit={handleAnalyze} loading={loading} />
          {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}

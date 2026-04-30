import { useState } from "react";
import { useNavigate } from "react-router-dom";
import RepoInputForm from "../components/RepoInputForm";
import { analyzeRepository } from "../services/repositoryService";

export default function LandingPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);

  const navigate = useNavigate();

  const steps = [
    "Fetching repo",
    "Parsing files",
    "AI Analysis",
    "Finalizing",
  ];

  const handleAnalyze = async (repoUrl: string) => {
    setLoading(true);
    setError(null);
    setProgressStep(0);

    const interval = setInterval(() => {
      setProgressStep((prev) => {
        if (prev < steps.length - 1) return prev + 1;
        return prev;
      });
    }, 2500);

    try {
      const result = await analyzeRepository(repoUrl);

      clearInterval(interval);
      setProgressStep(steps.length - 1);

      setTimeout(() => {
        navigate(`/repo/${result.repository.id}`);
      }, 500);
    } catch (err: any) {
      clearInterval(interval);
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

          <h1 className="mt-6 text-5xl font-bold tracking-tight">
            Codelens.ai
          </h1>

          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Paste a public GitHub repository URL and get metadata, file insights,
            risk detection, AI summaries, and a grounded repository chatbot in
            one dashboard.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {[
              "Repository metadata and codebase structure",
              "Language breakdown and file explorer",
              "Security and code-quality findings",
              "RAG-style chat grounded in repository content",
            ].map((feature) => (
              <div key={feature} className="card p-4 text-slate-300">
                {feature}
              </div>
            ))}
          </div>
        </div>

        <div>
          <RepoInputForm onSubmit={handleAnalyze} loading={loading} />

          {loading && (
            <div className="mt-6 rounded-2xl border border-cyan-500/20 bg-slate-900/70 p-5 shadow-lg">
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-100">
                  Analyzing repository...
                </p>
                <p className="text-sm text-slate-400">
                  {progressStep + 1}/{steps.length}
                </p>
              </div>

              <div className="mb-5 h-2 w-full overflow-hidden rounded-full bg-slate-700">
                <div
                  className="h-full rounded-full bg-cyan-400 transition-all duration-700"
                  style={{
                    width: `${((progressStep + 1) / steps.length) * 100}%`,
                  }}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-4">
                {steps.map((step, index) => (
                  <div
                    key={step}
                    className={`rounded-xl border p-3 text-center text-sm font-medium transition ${
                      index <= progressStep
                        ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-300"
                        : "border-slate-700 bg-slate-800/60 text-slate-500"
                    }`}
                  >
                    {step}
                  </div>
                ))}
              </div>
            </div>
          )}

          {error ? (
            <p className="mt-4 text-sm text-rose-300">{error}</p>
          ) : null}
        </div>
      </section>
    </main>
  );
}

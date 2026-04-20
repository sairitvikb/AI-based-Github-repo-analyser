import { RepositoryRisk } from "../types";

interface Props {
  risks: RepositoryRisk[];
}

const severityClasses: Record<string, string> = {
  low: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30",
  medium: "bg-amber-500/10 text-amber-300 border border-amber-500/30",
  high: "bg-rose-500/10 text-rose-300 border border-rose-500/30",
};

const severityLabelClasses: Record<string, string> = {
  low: "text-emerald-300",
  medium: "text-amber-300",
  high: "text-rose-300",
};

export default function RiskPanel({ risks }: Props) {
  const sortedRisks = [...risks].sort((a, b) => {
    const rank: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3);
  });

  return (
    <section className="card p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-white">Security & Quality Findings</h3>
          <p className="mt-1 text-sm text-slate-400">
            Lightweight risk signals identified from the analyzed repository snapshot.
          </p>
        </div>

        <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs font-medium text-slate-300">
          {sortedRisks.length} findings
        </span>
      </div>

      <div className="mt-5 space-y-4">
        {sortedRisks.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
            <p className="text-sm leading-6 text-slate-400">
              No major risks were detected in the current analysis snapshot.
            </p>
          </div>
        ) : (
          sortedRisks.map((risk) => (
            <article
              key={risk.id}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 transition-all duration-200 hover:border-slate-700 hover:bg-slate-900/80"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-semibold text-slate-100">{risk.title}</p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${
                        severityClasses[risk.severity] || severityClasses.low
                      }`}
                    >
                      {risk.severity}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-slate-300">{risk.description}</p>

                  {risk.file_path ? (
                    <div className="mt-3 rounded-lg bg-slate-900/80 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Affected file
                      </p>
                      <p className="mt-1 break-all text-sm text-cyan-300">{risk.file_path}</p>
                    </div>
                  ) : (
                    <div className="mt-3 rounded-lg bg-slate-900/80 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Scope
                      </p>
                      <p
                        className={`mt-1 text-sm ${
                          severityLabelClasses[risk.severity] || "text-slate-300"
                        }`}
                      >
                        Repository-wide signal
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
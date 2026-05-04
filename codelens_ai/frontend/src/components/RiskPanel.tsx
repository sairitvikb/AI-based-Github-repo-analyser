import { RepositoryRisk } from "../types";

type RiskPanelProps = {
  risks: RepositoryRisk[];
  onFileSelect?: (filePath: string) => void;
};

const severityStyles: Record<string, string> = {
  high: "border-rose-400/30 bg-rose-400/10 text-rose-300",
  medium: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  low: "border-cyan-400/30 bg-cyan-400/10 text-cyan-300",
};

export default function RiskPanel({ risks, onFileSelect }: RiskPanelProps) {
  return (
    <section className="card p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Security & Quality Findings
          </h2>
          <p className="mt-1 text-slate-400">
            Click a finding to jump to the affected file insight.
          </p>
        </div>

        <span className="rounded-full border border-slate-700 px-4 py-1 text-sm text-slate-300">
          {risks.length} findings
        </span>
      </div>

      <div className="space-y-4">
        {risks.length === 0 ? (
          <p className="text-sm text-slate-400">No risks detected.</p>
        ) : (
          risks.map((risk, index) => {
            const canClick = Boolean(risk.file_path && onFileSelect);

            return (
              <button
                key={`${risk.title}-${risk.file_path || index}`}
                type="button"
                disabled={!canClick}
                onClick={() => {
                  if (risk.file_path) onFileSelect?.(risk.file_path);
                }}
                className={`w-full rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-left transition ${
                  canClick
                    ? "cursor-pointer hover:-translate-y-1 hover:border-cyan-400/40 hover:bg-slate-900"
                    : "cursor-default"
                }`}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-lg font-semibold text-white">
                    {risk.title}
                  </h3>

                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                      severityStyles[risk.severity?.toLowerCase()] ||
                      "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {risk.severity}
                  </span>
                </div>

                <p className="mt-3 text-slate-300">{risk.description}</p>

                {risk.file_path && (
                  <div className="mt-4 rounded-xl bg-slate-900 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                      Affected File
                    </p>
                    <p className="mt-1 text-cyan-300">{risk.file_path}</p>
                    <p className="mt-2 text-xs text-slate-500">
                      Click to open file insight →
                    </p>
                  </div>
                )}
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}

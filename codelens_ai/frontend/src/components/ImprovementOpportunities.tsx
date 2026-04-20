// frontend/src/components/ImprovementOpportunities.tsx

import type { ImprovementItem } from "../types/improvement";

type Props = {
  improvements: ImprovementItem[];
};

const priorityStyles: Record<string, string> = {
  High: "bg-red-500/15 text-red-300 border border-red-500/30",
  Medium: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
  Low: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
};

export default function ImprovementOpportunities({ improvements }: Props) {
  if (!improvements.length) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Improvement Opportunities</h2>
        </div>
        <p className="text-sm text-slate-400">
          No major improvement suggestions were generated for this repository.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Improvement Opportunities</h2>
          <p className="mt-1 text-sm text-slate-400">
            Actionable engineering recommendations generated from repository signals.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {improvements.map((item, index) => (
          <div
            key={`${item.title}-${index}`}
            className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-slate-100">{item.title}</h3>
              <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
                {item.category}
              </span>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  priorityStyles[item.priority] ?? "bg-slate-700 text-slate-200"
                }`}
              >
                {item.priority}
              </span>
            </div>

            <p className="text-sm leading-6 text-slate-300">{item.description}</p>

            <div className="mt-3 rounded-lg bg-slate-900/80 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Why this matters
              </p>
              <p className="mt-1 text-sm leading-6 text-slate-300">{item.rationale}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
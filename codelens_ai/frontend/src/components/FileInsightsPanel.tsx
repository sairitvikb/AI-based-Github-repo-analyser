import { FileInsight } from "../types";

interface Props {
  files: FileInsight[];
}

function getComplexityClasses(score: number) {
  if (score >= 8) {
    return "bg-rose-500/15 text-rose-300 border border-rose-500/30";
  }
  if (score >= 5) {
    return "bg-amber-500/15 text-amber-300 border border-amber-500/30";
  }
  return "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30";
}

function cleanSummary(summary: string) {
  return summary
    .replace(/<[^>]+>/g, " ")
    .replace(/!\[.*?\]\(.*?\)/g, " ")
    .replace(/\[(.*?)\]\(.*?\)/g, "$1")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export default function FileInsightsPanel({ files }: Props) {
  return (
    <section className="card p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-white">File Insights</h3>
          <p className="mt-1 text-sm text-slate-400">
            High-signal files selected from the analyzed repository.
          </p>
        </div>
        <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs font-medium text-slate-300">
          {files.length} files
        </span>
      </div>

      <div className="mt-5 grid gap-4">
        {files.map((file) => (
          <article
            key={file.id}
            className="group rounded-2xl border border-slate-800 bg-slate-950/60 p-4 transition-all duration-200 hover:border-slate-700 hover:bg-slate-900/80"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-lg font-semibold text-cyan-300">
                  {file.path}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300">
                  {file.language || "Unknown"}
                </span>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${getComplexityClasses(
                    file.complexity_score
                  )}`}
                >
                  Complexity {file.complexity_score}/10
                </span>
              </div>
            </div>

            <div className="mt-3 overflow-hidden rounded-xl bg-slate-900/70 p-4">
              <p className="line-clamp-3 text-sm leading-6 text-slate-300">
                {cleanSummary(file.summary)}
              </p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
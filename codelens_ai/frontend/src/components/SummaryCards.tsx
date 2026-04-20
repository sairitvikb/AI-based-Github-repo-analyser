import { RepositoryDetail, RepositorySummary } from "../types";

interface Props {
  repository: RepositoryDetail;
  summary: RepositorySummary;
}

export default function SummaryCards({ repository, summary }: Props) {
  const stats = [
    { label: "Stars", value: repository.stars },
    { label: "Forks", value: repository.forks },
    { label: "Open Issues", value: repository.open_issues },
    { label: "Files Analyzed", value: repository.total_files_analyzed },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((item) => (
          <div key={item.label} className="card p-5">
            <p className="text-sm text-slate-400">{item.label}</p>
            <p className="mt-2 text-3xl font-bold">{item.value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <h3 className="text-lg font-semibold">Concise Summary</h3>
          <p className="mt-3 text-slate-300">{summary.concise_summary}</p>
        </div>
        <div className="card p-6">
          <h3 className="text-lg font-semibold">Architecture Summary</h3>
          <p className="mt-3 text-slate-300">{summary.architecture_summary}</p>
        </div>
      </div>
    </div>
  );
}

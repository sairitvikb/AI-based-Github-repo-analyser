import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface Props {
  languageBreakdown: Record<string, number>;
}

const COLORS = [
  "#22d3ee",
  "#8b5cf6",
  "#14b8a6",
  "#f59e0b",
  "#ef4444",
  "#3b82f6",
  "#84cc16",
  "#f97316",
  "#94a3b8",
];

function formatNumber(value: number) {
  return value.toLocaleString();
}

function formatChartData(languageBreakdown: Record<string, number>) {
  const entries = Object.entries(languageBreakdown)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1]);

  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  const topEntries = entries.slice(0, 6);
  const remainingEntries = entries.slice(6);

  const otherValue = remainingEntries.reduce((sum, [, value]) => sum + value, 0);

  const mergedEntries =
    otherValue > 0 ? [...topEntries, ["Other", otherValue] as [string, number]] : topEntries;

  return mergedEntries.map(([name, value]) => ({
    name,
    value,
    percent: total ? (value / total) * 100 : 0,
  }));
}

export default function LanguageChart({ languageBreakdown }: Props) {
  const data = formatChartData(languageBreakdown);

  return (
    <section className="card p-6">
      <div className="mb-5">
        <h3 className="text-xl font-semibold text-white">Language Distribution</h3>
        <p className="mt-1 text-sm text-slate-400">
          Top languages in the analyzed repository.
        </p>
      </div>

      {data.length === 0 ? (
        <div className="flex h-[320px] items-center justify-center text-slate-400">
          No language data available.
        </div>
      ) : (
        <div className="grid items-center gap-6 lg:grid-cols-[1.1fr,0.9fr]">
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={72}
                  outerRadius={138}
                  paddingAngle={1.5}
                  stroke="#e2e8f0"
                  strokeWidth={1}
                  label={false}
                  labelLine={false}
                >
                  {data.map((entry, index) => (
                    <Cell
                      key={`cell-${entry.name}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>

                <Tooltip
                  formatter={(value: number, name: string, item: any) => [
                    `${formatNumber(value)} (${item.payload.percent.toFixed(1)}%)`,
                    name,
                  ]}
                  contentStyle={{
                    backgroundColor: "#020617",
                    border: "1px solid #1e293b",
                    borderRadius: "12px",
                    color: "#e2e8f0",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-3">
            {data.map((entry, index) => (
              <div
                key={entry.name}
                className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span
                    className="h-3.5 w-3.5 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="truncate text-sm font-medium text-slate-100">
                    {entry.name}
                  </span>
                </div>

                <div className="shrink-0 text-right">
                  <div className="text-sm font-medium text-slate-200">
                    {formatNumber(entry.value)}
                  </div>
                  <div className="text-xs text-slate-400">
                    {entry.percent.toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
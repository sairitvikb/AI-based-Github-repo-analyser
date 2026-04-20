import { FormEvent, useState } from "react";

interface Props {
  onSubmit: (repoUrl: string) => Promise<void>;
  loading: boolean;
}

export default function RepoInputForm({ onSubmit, loading }: Props) {
  const [repoUrl, setRepoUrl] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await onSubmit(repoUrl);
  };

  return (
    <form onSubmit={handleSubmit} className="card p-6">
      <label className="mb-3 block text-sm font-medium text-slate-300">GitHub Repository URL</label>
      <div className="flex flex-col gap-3 md:flex-row">
        <input
          type="url"
          required
          value={repoUrl}
          onChange={(event) => setRepoUrl(event.target.value)}
          placeholder="https://github.com/owner/repository"
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none ring-0 placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Analyzing..." : "Analyze Repository"}
        </button>
      </div>
      <p className="mt-3 text-sm text-slate-400">Public repositories work out of the box. Add a GitHub token in the backend for better rate limits.</p>
    </form>
  );
}

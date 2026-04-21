# CodeLens AI

CodeLens AI is a production-style full-stack GitHub repository analysis platform built for interview presentations. A user can paste a public GitHub repository URL and get repository metadata, codebase analysis, language breakdown, file-level insights, AI-generated summaries, security/code-quality findings, and a grounded repository chat experience.

## Why this project is strong for interviews

- Shows full-stack engineering with React + TypeScript + FastAPI
- Demonstrates practical AI usage with retrieval-style repository chat
- Highlights engineering tradeoffs around GitHub API rate limits, chunking, and analysis scope
- Uses modular architecture, tests, environment-based config, and good developer experience

## Folder structure

```text
codelens_ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── .env.example
│   └── package.json
└── README.md
```

## Backend API

- `POST /api/v1/analyze`
- `GET /api/v1/repo/{repo_id}`
- `GET /api/v1/repo/{repo_id}/files`
- `GET /api/v1/repo/{repo_id}/summary`
- `GET /api/v1/repo/{repo_id}/risks`
- `POST /api/v1/repo/{repo_id}/chat`
- `GET /api/v1/health`

## Architecture and design decisions

### Why FastAPI
FastAPI is a strong choice for interview-quality Python backends because it offers clean request validation with Pydantic, automatic docs, async-ready performance, and readable code.

### Why RAG-style chat
Instead of asking an LLM to guess based on repository metadata, the app indexes repository chunks into a vector store and retrieves the most relevant snippets first. That makes answers more grounded and explainable.

### Why chunk repository files
Repositories contain long source files. Chunking keeps retrieval focused, reduces noisy context, and lets the system cite the file paths that informed the answer.

### Why a vector database
A vector store makes semantic search over code and docs practical. For a demo, ChromaDB is lightweight and easy to run locally.

### Tradeoffs made
- The app limits file count and file size for speed and predictable demo performance.
- It ignores binaries and build outputs to keep retrieval quality high.
- The current LLM service includes a fallback synthesized answer path so the demo still works without a paid API key.

## Local setup

### 1) Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### 2) Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```






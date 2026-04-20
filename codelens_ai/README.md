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

### 3) Open the app

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Environment variables

### Backend
- `GITHUB_TOKEN`: recommended for higher GitHub API rate limits
- `OPENAI_API_KEY`: optional for future provider-backed responses
- `LLM_PROVIDER`: abstraction switch for future OpenAI/Ollama/Groq/OpenRouter support

### Frontend
- `VITE_API_BASE_URL`: backend base URL

## Tests

```bash
cd backend
pytest -q
```

## Suggested demo flow for interview presentation

1. Start on the landing page and explain the problem: onboarding to unfamiliar repositories is slow.
2. Paste a public GitHub repo URL and run analysis.
3. Walk through metadata, language distribution, and file insights.
4. Show the security/code-quality findings panel.
5. Ask the chat a grounded question like: “Where is authentication implemented?”
6. Explain chunking, vector search, and why responses cite source files.
7. Close with tradeoffs and production improvements.

## Possible future improvements

- Background jobs for large repository analysis
- True provider abstraction with OpenAI, Ollama, Groq, and OpenRouter implementations
- Redis caching for repeated repo analyses
- User authentication and saved analyses
- Better static analysis with AST parsing and secret scanning libraries
- Streaming chat responses
- Async GitHub fetching and batching for faster large-repo performance
- Better ranking for retrieval and hybrid search over code + metadata

## Notes for your interview

Use these talking points:
- I chose FastAPI for typed APIs, clean structure, and speed of development.
- I used retrieval-based chat so answers are grounded in repository content instead of being generic.
- I chunk repository files to balance context quality and response speed.
- I capped analysis size to keep the MVP fast and predictable, which is a practical engineering tradeoff.
- For production, I would move analysis to async jobs, add caching, and support larger repos with pagination and smarter filtering.

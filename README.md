# CodeLens AI — AI-Powered GitHub Repository Analyzer

CodeLens AI is a full-stack application that analyzes public GitHub repositories and turns them into actionable engineering insights.  
It helps developers quickly understand a codebase by generating AI-powered summaries, identifying risks, surfacing improvement opportunities, and highlighting important files.

## Features

- Analyze any public GitHub repository from its URL
- Generate AI-powered repository summaries
- Show architecture and onboarding insights
- Detect potential risks such as:
  - missing tests
  - missing documentation
  - large or complex files
  - potential hardcoded secrets
- Suggest practical code and project improvements
- Display file-level insights for key repository files
- Interactive frontend dashboard for exploring analysis results

## Tech Stack

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS

### Backend
- FastAPI
- Python
- SQLAlchemy
- Pydantic

### AI / Intelligence
- Groq API
- LLM-based repository summarization
- Heuristic code analysis

### Deployment
- Render

## How It Works

1. User enters a GitHub repository URL
2. Backend fetches repository metadata and selected file contents using the GitHub API
3. The system analyzes files for:
   - summaries
   - complexity
   - risks
   - improvements
4. Groq generates high-level repository summaries
5. Results are stored and displayed in a clean dashboard

## Project Structure

```bash
codelens_ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   └── public/
│
└── README.md
```
## 🎯 Example Use Cases

- Understand unfamiliar repositories quickly  
- Prepare for technical interviews  
- Accelerate developer onboarding  
- Evaluate open-source projects  
- Detect maintainability issues early  
- Perform lightweight engineering due diligence  

---

## ⚙️ Local Setup

### 📥 Clone Repository

```bash
git clone https://github.com/sairitvikb/AI-based-Github-repo-analyser.git
cd AI-based-Github-repo-analyser/codelens_ai
```
## 🖥️ Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
## 🌐 Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

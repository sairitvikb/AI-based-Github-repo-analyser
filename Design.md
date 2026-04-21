# CodeLens AI — Design Document

## 1. Overview

CodeLens AI is a full-stack AI-powered GitHub Repository Analyzer that helps users quickly understand unfamiliar repositories by generating intelligent summaries, architecture insights, risk reports, improvement suggestions, and file-level insights.

The platform reduces manual repository review time from hours to minutes using automation, AI summarization, and repository intelligence.

---

## 2. Problem Statement

Developers, recruiters, and engineering managers often need to understand unfamiliar codebases quickly.

### Current Pain Points

- Reading hundreds of files manually  
- Slow onboarding into new repositories  
- Difficulty understanding architecture  
- Hidden maintainability risks  
- No quick technical summaries  

CodeLens AI solves this by automatically analyzing repositories and presenting actionable insights.

---

## 3. Goals

### Functional Goals

- Accept public GitHub repository URLs  
- Fetch repository metadata and source files  
- Generate AI-powered summaries  
- Detect risks and code quality issues  
- Suggest improvements  
- Provide file-level insights  
- Present results in an interactive dashboard  

### Non-Functional Goals

- Fast response time  
- Scalable architecture  
- Clean UI/UX  
- Cloud deployable  
- Maintainable codebase  

---

## 4. High-Level Architecture

```text
User
 ↓
React Frontend
 ↓
FastAPI Backend API
 ↓
Repository Service Layer
 ↓
GitHub API + AI Engine
 ↓
Database
```
## Class diagram
```mermaid
classDiagram
    class RepositoryService {
        +analyze_repository()
        +get_repository()
        +get_summary()
        +get_risks()
        +get_improvements()
        +chat()
    }

    class GitHubService {
        +parse_repo_url()
        +get_repository_metadata()
        +fetch_repository_files()
        +get_file_content()
    }

    class AnalysisService {
        +summarize_file()
        +estimate_complexity()
        +detect_risks()
        +suggest_improvements()
        +build_repo_summary()
    }

    class LLMService {
        +answer_question()
    }

    class VectorStoreService {
        +reset_collection()
        +upsert_chunks()
        +search()
    }

    RepositoryService --> GitHubService
    RepositoryService --> AnalysisService
    RepositoryService --> LLMService
    RepositoryService --> VectorStoreService
```
## Data Model Class Diagram
```mermaid
classDiagram
    class Repository {
        +id: int
        +repo_url: string
        +owner: string
        +name: string
        +description: string
        +default_branch: string
        +stars: int
        +forks: int
        +open_issues: int
        +primary_language: string
    }

    class RepositorySummary {
        +concise_summary: string
        +detailed_summary: string
        +architecture_summary: string
        +onboarding_summary: string
    }

    class RepositoryRisk {
        +title: string
        +severity: string
        +description: string
    }

    class RepositoryImprovement {
        +title: string
        +priority: string
        +description: string
    }

    class FileInsight {
        +path: string
        +language: string
        +summary: string
        +complexity_score: int
    }

    Repository --> RepositorySummary
    Repository --> RepositoryRisk
    Repository --> RepositoryImprovement
    Repository --> FileInsight
```
## Request / Response Flow Diagram
```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant GitHub
    participant AI
    participant DB

    User->>Frontend: Enter GitHub URL
    Frontend->>Backend: POST /analyze
    Backend->>GitHub: Fetch repo files
    Backend->>AI: Generate summaries
    Backend->>DB: Save results
    Backend-->>Frontend: Return dashboard data
```

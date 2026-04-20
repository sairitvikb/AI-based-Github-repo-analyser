from __future__ import annotations

import os
import re

from openai import OpenAI

from app.schemas.chat import ChatResponse, ChatSource


class LLMService:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def answer_question(self, question: str, context_chunks: list[dict]) -> ChatResponse:
        if not context_chunks:
            return ChatResponse(
                answer="I could not find enough repository context to answer that question.",
                sources=[],
            )

        ranked_chunks = self._rank_chunks_for_question(question, context_chunks)
        sources = self._build_sources(ranked_chunks)

        if self.provider == "openai" and self.openai_api_key:
            try:
                answer = self._answer_with_openai(question, ranked_chunks)
                return ChatResponse(answer=answer, sources=sources)
            except Exception as exc:
                return ChatResponse(
                     answer=f"OpenAI call failed: {exc}",
                     sources=sources,
                )


        return ChatResponse(
            answer=self._fallback_answer(question, ranked_chunks),
            sources=sources,
        )

    def _rank_chunks_for_question(self, question: str, chunks: list[dict]) -> list[dict]:
        q = question.lower()
        file_targets = self._extract_file_targets(q)
        query_terms = self._extract_query_terms(q)

        ranked = []
        seen = set()

        for chunk in chunks:
            path = chunk.get("file_path", "unknown")
            content = (chunk.get("content") or "").strip()
            if not content:
                continue

            key = (path, content[:180])
            if key in seen:
                continue
            seen.add(key)

            path_lower = path.lower()
            content_lower = content.lower()
            score = int(chunk.get("priority", 0))

            # exact file targeting
            for target in file_targets:
                if target in path_lower:
                    score += 120
                elif target.replace(".py", "") in path_lower:
                    score += 70

            # setup questions
            if self._is_setup_question(q):
                if any(name in path_lower for name in [
                    "readme.md", "pyproject.toml", "requirements.txt",
                    "package.json", "docker-compose", "makefile"
                ]):
                    score += 80

            # summary questions
            if self._is_summary_question(q):
                if "readme" in path_lower:
                    score += 60
                if any(token in path_lower for token in ["__init__.py", "package.json", "pyproject.toml"]):
                    score += 30

            # onboarding questions
            if self._is_onboarding_question(q):
                if "readme" in path_lower:
                    score += 70
                if any(token in path_lower for token in [
                    "pyproject.toml", "requirements.txt", "package.json",
                    "docker-compose", "main.py", "app.py", "__init__.py"
                ]):
                    score += 40

            # auth questions
            if any(token in q for token in ["auth", "authentication", "login", "jwt", "oauth"]):
                if any(token in path_lower for token in ["auth", "security", "login", "jwt", "oauth"]):
                    score += 60

            for term in query_terms:
                if term in path_lower:
                    score += 12
                if term in content_lower:
                    score += 4

            ranked.append(
                {
                    "file_path": path,
                    "content": content,
                    "priority": chunk.get("priority", 0),
                    "score": score,
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:5]

    def _answer_with_openai(self, question: str, ranked_chunks: list[dict]) -> str:
        client = OpenAI(api_key=self.openai_api_key)
        context_block = self._build_context_block(ranked_chunks)

        system_prompt = (
            "You are a repository copilot. "
            "Answer naturally and clearly like ChatGPT, but stay grounded in the provided repository context only. "
            "If the user asks how to run/setup the project, prioritize README and dependency/config files. "
            "If the user asks what a specific file does, prioritize exact file matches. "
            "If the context is weak, say that clearly instead of guessing. "
            "Keep answers concise but useful."
        )

        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Repository context:\n{context_block}\n\n"
            "Answer the question using the repository context. "
            "Mention the most relevant files naturally in the answer."
        )

        response = client.chat.completions.create(
            model=self.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return (response.choices[0].message.content or "").strip()

    def _fallback_answer(self, question: str, ranked_chunks: list[dict]) -> str:
        paths = [c["file_path"] for c in ranked_chunks[:3]]
        if self._is_setup_question(question.lower()):
            return (
                f"From the retrieved repository context, the best setup-related files appear to be {', '.join(paths)}. "
                "Start with the README, then check dependency/configuration files, and then run the documented commands."
            )
        if self._is_summary_question(question.lower()):
            return (
                f"This repository appears to be represented best by {', '.join(paths)}. "
                "Start with the README for the high-level purpose, then review the main package or entry-point files."
            )
        return (
            f"The most relevant files I found are {', '.join(paths)}. "
            "The current non-LLM fallback is limited, so the answer may be less precise."
        )

    def _build_sources(self, ranked_chunks: list[dict]) -> list[ChatSource]:
        sources = []
        for chunk in ranked_chunks[:4]:
            sources.append(
                ChatSource(
                    file_path=chunk["file_path"],
                    snippet=self._clean_text(chunk["content"])[:220],
                )
            )
        return sources

    def _build_context_block(self, ranked_chunks: list[dict]) -> str:
        blocks = []
        for chunk in ranked_chunks:
            blocks.append(
                f"FILE: {chunk['file_path']}\n"
                f"CONTENT:\n{self._clean_text(chunk['content'])[:1600]}"
            )
        return "\n\n---\n\n".join(blocks)

    def _extract_file_targets(self, question: str) -> list[str]:
        return [
            match.lower()
            for match in re.findall(
                r"\b[\w./-]+\.(?:py|ts|tsx|js|jsx|java|go|rs|json|yml|yaml|md|toml)\b",
                question,
            )
        ]

    def _extract_query_terms(self, question: str) -> list[str]:
        stopwords = {
            "the", "a", "an", "and", "or", "to", "of", "for", "is", "are", "in", "on",
            "what", "where", "how", "why", "which", "does", "do", "this", "that", "repo",
            "repository", "file", "files", "new", "developer", "read", "first", "project",
            "locally", "run", "setup",
        }
        return [
            token for token in re.findall(r"[a-zA-Z_]{3,}", question)
            if token not in stopwords
        ]

    def _is_setup_question(self, q: str) -> bool:
        return any(p in q for p in [
            "how would i run this project locally",
            "how do i run this project locally",
            "how do i run this",
            "how to run this",
            "how do i set up",
            "how to set up",
            "install",
            "setup",
        ])

    def _is_summary_question(self, q: str) -> bool:
        return any(p in q for p in [
            "what does this repository do",
            "what does this repo do",
            "what is this repository",
            "what is this repo",
            "summarize this repo",
            "main summary",
            "overview",
        ])

    def _is_onboarding_question(self, q: str) -> bool:
        return any(p in q for p in [
            "which files should a new developer read first",
            "which files should i read first",
            "where should i start",
            "key files to read",
        ])

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        text = re.sub(r"http[s]?://\S+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
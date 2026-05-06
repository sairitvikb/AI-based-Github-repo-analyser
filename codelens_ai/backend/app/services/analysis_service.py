from __future__ import annotations

import math
import re
from collections import Counter

from app.core.config import settings
from app.schemas.repository import RepositorySummaryData
from app.utils.repository_filters import infer_language_from_path

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "Possible OpenAI-style API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Possible AWS access key"),
    (
        re.compile(r'''(?i)(api[_-]?key|secret|token)\s*[:=]\s*["'][^"']{8,}'''),
        "Hardcoded secret-like assignment",
    ),
]


class AnalysisService:
    def summarize_file(self, path: str, content: str) -> str:
        language = infer_language_from_path(path) or "text"
        lower_path = path.lower()
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if not lines:
            return "No meaningful content detected."

        filename = lower_path.split("/")[-1]

        # AI-powered summaries for important code files
        if self._should_use_ai_file_summary(lower_path, content):
            ai_summary = self._generate_ai_file_summary(path, content)
            if ai_summary:
                return ai_summary

        if filename == "readme.md":
            return "Top-level README describing the repository purpose, setup flow, usage instructions, and main developer entry points."

        if lower_path.endswith(".md"):
            heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), "")
            if heading:
                return f"Documentation focused on {heading}, useful for setup, onboarding, or developer reference."
            return "Markdown documentation used for onboarding, setup instructions, or technical reference."

        if lower_path.endswith(("docker-compose.yml", "docker-compose.yaml")):
            return "Docker Compose configuration defining local services, dependencies, and development environment startup."

        if lower_path.endswith((".yml", ".yaml")):
            if ".github/workflows/" in lower_path:
                return "CI/CD workflow used for automated testing, linting, builds, or deployment."
            return "YAML configuration used for automation, environment settings, or build tooling."

        if lower_path.endswith(".json"):
            if "package.json" in lower_path:
                return "JavaScript package manifest defining dependencies, scripts, and frontend/backend tooling metadata."
            return "JSON configuration or metadata file storing structured project settings."

        if lower_path.endswith(".py"):
            imports = self._extract_imports(content)
            functions = self._count_matches(r"^\s*(async\s+def|def)\s+\w+", content)
            classes = self._count_matches(r"^\s*class\s+\w+", content)

            if "__init__.py" in lower_path:
                return "Package initializer that organizes module exports and makes this directory importable."

            if "test" in lower_path:
                tested_area = filename.replace("test_", "").replace("_test", "").replace(".py", "")
                tested_area = tested_area.replace("_", " ").strip() or "core functionality"

                details = []
                if functions:
                    details.append(f"{functions} test/helper function{'s' if functions != 1 else ''}")
                if classes:
                    details.append(f"{classes} test class{'es' if classes != 1 else ''}")
                if imports:
                    details.append(f"dependencies such as {', '.join(imports[:3])}")

                extra = f" It includes {', '.join(details)}." if details else ""
                return (
                    f"Automated test suite focused on {tested_area}, validating expected behavior, "
                    f"edge cases, and regression safety for that part of the codebase.{extra}"
                )

            if "exception" in lower_path:
                return "Defines custom exception classes used to keep error handling consistent across the module."

            if "parser" in lower_path:
                return "Implements parsing logic that converts raw input into validated internal structures."

            if "model" in lower_path or "schema" in lower_path:
                return "Defines structured data models or schemas used for validation, persistence, or API responses."

            if "config" in lower_path or "settings" in lower_path:
                return "Centralizes configuration logic and environment-driven settings for the application."

            if "api" in lower_path or "route" in lower_path:
                return "Implements API routes or request handlers that expose application functionality to external clients."

            if "service" in lower_path:
                return "Contains service-layer business logic or orchestration used by higher-level application flows."

            parts = [f"{language} implementation file"]
            if classes > 0:
                parts.append(f"defines {classes} class{'es' if classes != 1 else ''}")
            if functions > 0:
                parts.append(f"includes {functions} function{'s' if functions != 1 else ''}")
            if imports:
                parts.append(f"uses modules such as {', '.join(imports[:4])}")

            if len(parts) > 1:
                return ", ".join(parts[:-1]) + ", and " + parts[-1] + "."

            return "Python implementation file containing core application logic."

        if lower_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            functions = self._count_matches(
                r"(function\s+\w+|const\s+\w+\s*=|export\s+default)",
                content,
            )

            if "component" in lower_path or lower_path.endswith(".tsx"):
                return "Frontend UI component responsible for rendering interactive application views or reusable interface sections."
            if "hook" in lower_path:
                return "Reusable frontend hook managing state, side effects, or shared UI behavior."
            if "service" in lower_path or "api" in lower_path:
                return "Client-side service layer responsible for API communication and integration with backend endpoints."
            if "type" in lower_path:
                return "TypeScript type definitions used to keep frontend data contracts consistent."
            if functions:
                return f"JavaScript/TypeScript source file containing UI or application logic with about {functions} exported or local function patterns."
            return "JavaScript or TypeScript source file containing UI or application logic."

        if lower_path.endswith(".html"):
            return "HTML template defining the base UI structure for the web application."

        if lower_path.endswith(".css"):
            return "Stylesheet defining layout, theme, spacing, and visual presentation rules."

        return f"{language} file containing implementation or configuration details."

    def _should_use_ai_file_summary(self, lower_path: str, content: str) -> bool:
        if not settings.groq_api_key:
            return False

        if len(content.strip()) < 250:
            return False

        ignored_extensions = (
            ".md",
            ".yml",
            ".yaml",
            ".json",
            ".lock",
            ".txt",
            ".css",
            ".html",
        )

        if lower_path.endswith(ignored_extensions):
            return False

        # Skip most test files so they stay fast and predictable
        if lower_path.startswith("tests/") or "/tests/" in lower_path:
            return False

        return lower_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx"))

    def _generate_ai_file_summary(self, path: str, content: str) -> str:
        try:
            from groq import Groq

            if not settings.groq_api_key:
                return ""

            client = Groq(api_key=settings.groq_api_key)

            snippet = content[:3500]

            prompt = f"""
You are a senior software engineer reviewing one file from a GitHub repository.

File path:
{path}

File content:
{snippet}

Write a useful file insight in 2 short sentences.

Explain:
- What this file actually does
- Why it matters in the repository

Rules:
- Do not count functions, classes, or imports.
- Do not say generic phrases like "contains logic" or "implementation file".
- Be specific and practical.
- Do not use markdown bullets.
- Keep it under 70 words.
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=140,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You explain source files like a senior engineer. "
                            "Focus on purpose, responsibility, and system role."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            summary = (response.choices[0].message.content or "").strip()
            return summary.replace("\n", " ").strip()

        except Exception as exc:
            print(f"AI file summary failed for {path}: {exc}")
            return ""

    def estimate_complexity(self, content: str) -> int:
        control_flow_hits = len(
            re.findall(r"\b(if|for|while|switch|case|except|catch|elif)\b", content)
        )
        nesting_penalty = content.count("{") + content.count(":\n")
        return min(10, max(1, math.ceil((control_flow_hits + nesting_penalty * 0.1) / 4)))

    def _infer_file_role(self, path: str) -> str:
        lower_path = path.lower()

        if "test" in lower_path:
            return "test file"
        if "model" in lower_path or "schema" in lower_path:
            return "data model"
        if "util" in lower_path or "helper" in lower_path:
            return "utility module"
        if "api" in lower_path or "route" in lower_path:
            return "API handler"
        if "service" in lower_path:
            return "service layer"
        if "component" in lower_path:
            return "UI component"
        if "config" in lower_path or "settings" in lower_path:
            return "configuration module"

        return "source module"

    def detect_risks(self, file_records: list[dict], repo_metadata: dict) -> list[dict]:
        risks: list[dict] = []
        has_readme = any(item["path"].lower().startswith("readme") for item in file_records)
        has_tests = any(item["is_test_file"] for item in file_records)

        if not has_readme:
            risks.append(
                {
                    "title": "Missing README",
                    "severity": "medium",
                    "description": "The repository does not include a visible README, which may slow down setup, onboarding, and contribution workflows.",
                    "file_path": None,
                }
            )

        if not has_tests:
            risks.append(
                {
                    "title": "Missing tests",
                    "severity": "medium",
                    "description": "No test files were detected in the analyzed subset, which increases regression risk for future changes.",
                    "file_path": None,
                }
            )

        for record in file_records:
            content = record["content"]
            path = record["path"]
            file_name = path.split("/")[-1]
            file_role = self._infer_file_role(path)

            for pattern, description in SECRET_PATTERNS:
                if pattern.search(content):
                    risks.append(
                        {
                            "title": "Potential hardcoded secret",
                            "severity": "high",
                            "description": f"{description} detected in `{file_name}`. Move secrets into environment variables or a secure secrets manager.",
                            "file_path": path,
                        }
                    )
                    break

            todo_count = len(re.findall(r"\b(TODO|FIXME|HACK)\b", content, flags=re.IGNORECASE))
            if todo_count >= 5:
                risks.append(
                    {
                        "title": "High TODO/FIXME density",
                        "severity": "low",
                        "description": f"`{file_name}` contains {todo_count} TODO/FIXME markers, which may indicate unfinished work or hidden technical debt.",
                        "file_path": path,
                    }
                )

            if record["size"] > settings.max_file_bytes * 0.85:
                risks.append(
                    {
                        "title": "Large source file",
                        "severity": "medium",
                        "description": f"`{file_name}` is relatively large for a {file_role}, which can make code review, debugging, and ownership harder.",
                        "file_path": path,
                    }
                )

            if record["complexity_score"] >= 8:
                risks.append(
                    {
                        "title": "High complexity file",
                        "severity": "medium",
                        "description": f"The {file_role} `{file_name}` has a complexity score of {record['complexity_score']}/10. This may reduce readability and increase bug risk, so consider splitting logic into smaller focused functions.",
                        "file_path": path,
                    }
                )

        if repo_metadata.get("open_issues_count", 0) > 50:
            risks.append(
                {
                    "title": "High open issue count",
                    "severity": "low",
                    "description": "A high issue count can indicate maintenance pressure, unresolved bugs, or a large backlog of improvement work.",
                    "file_path": None,
                }
            )

        return risks[:20]

    def suggest_improvements(self, file_records: list[dict], repo_metadata: dict) -> list[dict]:
        improvements: list[dict] = []

        has_readme = any(item["path"].lower().startswith("readme") for item in file_records)
        has_tests = any(item["is_test_file"] for item in file_records)
        has_ci = any(
            ".github/workflows/" in item["path"].lower() or "gitlab-ci" in item["path"].lower()
            for item in file_records
        )

        large_files = [item for item in file_records if item["size"] > 80000]
        complex_files = [item for item in file_records if item["complexity_score"] >= 8]
        todo_heavy_files = []

        for item in file_records:
            todo_count = len(re.findall(r"\b(TODO|FIXME|HACK)\b", item["content"], flags=re.IGNORECASE))
            if todo_count >= 4:
                todo_heavy_files.append(item)

        if not has_tests:
            improvements.append(
                {
                    "title": "Add automated test coverage",
                    "category": "Testing",
                    "priority": "High",
                    "description": "Introduce unit and integration tests for the most important flows in the repository.",
                    "rationale": "No strong test presence was detected in the analyzed files, which increases regression risk.",
                }
            )

        if not has_readme:
            improvements.append(
                {
                    "title": "Improve onboarding documentation",
                    "category": "Documentation",
                    "priority": "High",
                    "description": "Add or expand a README with setup steps, usage examples, and contribution guidance.",
                    "rationale": "Good documentation reduces onboarding time and makes the project easier to maintain.",
                }
            )

        if not has_ci:
            improvements.append(
                {
                    "title": "Add CI pipeline",
                    "category": "Developer Experience",
                    "priority": "Medium",
                    "description": "Set up a CI workflow to run tests, linting, and basic quality checks on each change.",
                    "rationale": "Automated validation improves reliability and catches issues earlier in development.",
                }
            )

        if large_files:
            improvements.append(
                {
                    "title": "Break down oversized files",
                    "category": "Maintainability",
                    "priority": "Medium",
                    "description": "Refactor large files into smaller modules with clearer responsibilities.",
                    "rationale": f"{len(large_files)} large file(s) were detected, which can make maintenance and review harder.",
                }
            )

        if complex_files:
            improvements.append(
                {
                    "title": "Reduce high-complexity modules",
                    "category": "Code Quality",
                    "priority": "Medium",
                    "description": "Refactor files with heavy branching or mixed responsibilities into simpler components.",
                    "rationale": f"{len(complex_files)} file(s) showed high estimated complexity, which may affect readability and change safety.",
                }
            )

        if todo_heavy_files:
            improvements.append(
                {
                    "title": "Address TODO and FIXME backlog",
                    "category": "Code Quality",
                    "priority": "Low",
                    "description": "Review unfinished work markers and convert them into tracked issues or completed improvements.",
                    "rationale": f"{len(todo_heavy_files)} file(s) contain a high density of TODO/FIXME markers.",
                }
            )

        if repo_metadata.get("open_issues_count", 0) > 75:
            improvements.append(
                {
                    "title": "Review maintenance backlog",
                    "category": "Project Health",
                    "priority": "Low",
                    "description": "Audit recurring issue themes and prioritize high-value cleanup or stabilization work.",
                    "rationale": "A high open issue count may indicate maintenance pressure or unresolved technical debt.",
                }
            )

        if len(file_records) > 40:
            improvements.append(
                {
                    "title": "Add architecture documentation",
                    "category": "Scalability",
                    "priority": "Medium",
                    "description": "Document key modules, entry points, and system boundaries for faster repository understanding.",
                    "rationale": "Larger repositories benefit from explicit structure and architectural guidance for new contributors.",
                }
            )

        return improvements[:8]

    def build_repo_summary(
        self,
        repo_metadata: dict,
        file_records: list[dict],
    ) -> RepositorySummaryData:
        languages = Counter([record["language"] or "Unknown" for record in file_records])
        likely_stack = [language for language, _ in languages.most_common(6)]

        important_records = [
            item
            for item in file_records
            if not item["is_test_file"]
            and not item["path"].lower().endswith(
                (".md", ".yml", ".yaml", ".json", ".txt", ".lock")
            )
        ]

        selected_records = important_records[:25] if important_records else file_records[:25]

        top_files = "\n".join(
            [f"- {item['path']}: {item['summary']}" for item in selected_records]
        )

        repo_name = repo_metadata.get("name", "repository")
        description = repo_metadata.get("description") or "No description provided."

        prompt = f"""
You are a senior software engineer performing a practical architecture review.

Analyze this GitHub repository and create useful, non-redundant summaries.

Repository Name:
{repo_name}

GitHub Description:
{description}

Likely Technologies:
{", ".join(likely_stack)}

Important Implementation Files:
{top_files}

Return these 4 sections exactly in this format:

1. Concise Summary
<content>

2. Detailed Summary
<content>

3. Architecture Summary
<content>

4. Developer Onboarding Summary
<content>

Requirements:
- Focus on what the repository does, not just what files exist.
- Explain the main components, responsibilities, and developer workflow.
- Do not repeat the same files across sections.
- Do not over-focus on README, tests, setup files, or YAML config.
- Mention test/config files only if they are central to understanding the repo.
- Avoid generic phrases like "appears modular", "multiple modules", or "various files".
- Detailed Summary should explain the product/system in 3-4 useful sentences.
- Architecture Summary should explain layers, services, entry points, and data flow.
- Developer Onboarding Summary should give practical first steps for a new engineer.
- Keep Concise Summary to 2 lines max.
- Keep Architecture Summary to 3 lines max.
- Keep Developer Onboarding Summary to 3 lines max.
"""

        try:
            from groq import Groq

            if not settings.groq_api_key:
                raise ValueError("Missing GROQ_API_KEY")

            client = Groq(api_key=settings.groq_api_key)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.15,
                max_tokens=750,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior software engineer performing a practical "
                            "architecture review. Avoid redundant file listing. Explain "
                            "purpose, architecture, data flow, and onboarding steps clearly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            text = (response.choices[0].message.content or "").strip()

            concise = self._extract_section(text, "1. Concise Summary", "2. Detailed Summary")
            detailed = self._extract_section(text, "2. Detailed Summary", "3. Architecture Summary")
            architecture = self._extract_section(text, "3. Architecture Summary", "4. Developer Onboarding Summary")
            onboarding = self._extract_section(text, "4. Developer Onboarding Summary", None)

            if not concise:
                concise = f"{repo_name} is a software repository built using {', '.join(likely_stack[:3])}."
            if not detailed:
                detailed = (
                    f"{repo_name} focuses on {description}. The analyzed implementation files "
                    "show the main application logic, supporting services, and developer workflow."
                )
            if not architecture:
                architecture = (
                    "The codebase separates implementation logic, configuration, and external interfaces. "
                    "Developers should trace the main entry points first, then follow service-layer calls and data models."
                )
            if not onboarding:
                onboarding = (
                    "Start with the README or main entry point, install dependencies, run the project locally, "
                    "then review the core implementation files before tests and configuration."
                )

            return RepositorySummaryData(
                concise_summary=concise,
                detailed_summary=detailed,
                architecture_summary=architecture,
                onboarding_summary=onboarding,
                likely_stack=likely_stack,
            )

        except Exception as exc:
            print(f"Groq summary generation failed: {exc}")

            concise = f"{repo_name} is a software repository built using {', '.join(likely_stack[:3])}."
            detailed = (
                f"{repo_name} focuses on {description}. The analyzed implementation files "
                "show the main application logic, supporting services, and developer workflow."
            )
            architecture = (
                "The codebase separates implementation logic, configuration, and external interfaces. "
                "Developers should trace the main entry points first, then follow service-layer calls and data models."
            )
            onboarding = (
                "Start with the README or main entry point, install dependencies, run the project locally, "
                "then review the core implementation files before tests and configuration."
            )

            return RepositorySummaryData(
                concise_summary=concise,
                detailed_summary=detailed,
                architecture_summary=architecture,
                onboarding_summary=onboarding,
                likely_stack=likely_stack,
            )

    def _extract_imports(self, content: str) -> list[str]:
        imports = set()

        for match in re.findall(r"^\s*import\s+([\w\.]+)", content, flags=re.MULTILINE):
            imports.add(match.split(".")[0])

        for match in re.findall(
            r"^\s*from\s+([\w\.]+)\s+import",
            content,
            flags=re.MULTILINE,
        ):
            imports.add(match.split(".")[0])

        for match in re.findall(r'require\(["\']([^"\']+)["\']\)', content):
            imports.add(match.split("/")[0])

        return sorted(imports)

    def _count_matches(self, pattern: str, content: str) -> int:
        return len(re.findall(pattern, content, flags=re.MULTILINE))

    def _extract_section(self, text: str, start_marker: str, end_marker: str | None) -> str:
        start_index = text.find(start_marker)
        if start_index == -1:
            return ""

        start_index += len(start_marker)

        if end_marker is None:
            section = text[start_index:]
        else:
            end_index = text.find(end_marker, start_index)
            if end_index == -1:
                section = text[start_index:]
            else:
                section = text[start_index:end_index]

        return section.strip()

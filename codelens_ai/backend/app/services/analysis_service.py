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
    def __init__(self) -> None:
        self.ai_calls = 0
        self.max_ai_calls = 10

    def summarize_file(self, path: str, content: str) -> str:
        language = infer_language_from_path(path) or "text"
        lower_path = path.lower()
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if not lines:
            return "No meaningful content detected."

        filename = lower_path.split("/")[-1]

        if self._should_use_ai_file_summary(lower_path, content) and self.ai_calls < self.max_ai_calls:
            self.ai_calls += 1
            ai_summary = self._generate_ai_file_summary(path, content)
            if ai_summary:
                return ai_summary

        return self._fast_file_summary(path, content, language)

    def _fast_file_summary(self, path: str, content: str, language: str) -> str:
        lower_path = path.lower()
        filename = lower_path.split("/")[-1]
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if filename == "readme.md":
            return "Primary project documentation explaining purpose, setup, usage, and developer entry points."

        if lower_path.endswith(".md"):
            heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), "")
            if heading:
                return f"Documentation focused on {heading}, helping developers understand setup, usage, or project decisions."
            return "Markdown documentation used for setup, onboarding, or technical reference."

        if lower_path.endswith(("docker-compose.yml", "docker-compose.yaml")):
            return "Docker Compose configuration that defines local services, dependencies, and development startup flow."

        if lower_path.endswith((".yml", ".yaml")):
            if ".github/workflows/" in lower_path:
                return "CI/CD workflow that automates testing, linting, builds, or deployment checks."
            return "YAML configuration used for automation, environment settings, or build tooling."

        if lower_path.endswith(".json"):
            if "package.json" in lower_path:
                return "JavaScript package manifest defining dependencies, scripts, and project tooling."
            return "JSON configuration or metadata file storing structured project settings."

        if lower_path.endswith(".py"):
            functions = self._count_matches(r"^\s*(async\s+def|def)\s+\w+", content)
            classes = self._count_matches(r"^\s*class\s+\w+", content)
            imports = self._extract_imports(content)

            if "__init__.py" in lower_path:
                return "Package initializer that organizes module exports and makes the directory importable."

            if "test" in lower_path:
                tested_area = filename.replace("test_", "").replace("_test", "").replace(".py", "")
                tested_area = tested_area.replace("_", " ").strip() or "core functionality"
                return (
                    f"Automated test file validating {tested_area}. It protects the codebase from regressions by checking "
                    f"expected behavior, edge cases, and failure paths."
                )

            if "exception" in lower_path:
                return "Defines custom exception types so backend error handling stays consistent and easier to trace."

            if "parser" in lower_path:
                return "Parses raw input into structured internal data so later application logic can work with predictable objects."

            if "model" in lower_path or "schema" in lower_path:
                return "Defines data contracts used for validation, persistence, or API responses, keeping data flow consistent."

            if "config" in lower_path or "settings" in lower_path:
                return "Centralizes environment-driven configuration so local and deployed behavior can be managed safely."

            if "api" in lower_path or "route" in lower_path:
                return "Defines API handlers that connect external client requests to backend service logic and responses."

            if "service" in lower_path:
                return "Implements service-layer orchestration that coordinates business rules, data access, and application workflows."

            details = []
            if classes:
                details.append(f"{classes} class{'es' if classes != 1 else ''}")
            if functions:
                details.append(f"{functions} function{'s' if functions != 1 else ''}")
            if imports:
                details.append(f"dependencies like {', '.join(imports[:3])}")

            if details:
                return f"{filename} is a Python module with {', '.join(details)}, supporting core application behavior."

            return "Python source file containing application logic used by the repository."

        if lower_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            functions = self._count_matches(
                r"(function\s+\w+|const\s+\w+\s*=|export\s+default)",
                content,
            )

            if "component" in lower_path or lower_path.endswith(".tsx"):
                return "Frontend component that renders a user-facing screen or reusable interface section."
            if "hook" in lower_path:
                return "Reusable frontend hook that manages shared state, side effects, or UI behavior."
            if "service" in lower_path or "api" in lower_path:
                return "Client-side service layer that communicates with backend APIs and keeps network logic separate from UI code."
            if "type" in lower_path:
                return "TypeScript type definition file that keeps frontend data contracts predictable and safer to change."
            if functions:
                return f"JavaScript/TypeScript source file with about {functions} function patterns used for UI or application behavior."
            return "JavaScript or TypeScript source file containing frontend or application logic."

        if lower_path.endswith(".html"):
            return "HTML template defining the base structure used to mount or render the web application."

        if lower_path.endswith(".css"):
            return "Stylesheet controlling layout, spacing, colors, and visual presentation."

        return f"{language} file containing implementation or configuration details."

    def _should_use_ai_file_summary(self, lower_path: str, content: str) -> bool:
        if not settings.groq_api_key:
            return False

        if len(content.strip()) < 500:
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

        if "test" in lower_path:
            return False

        if "util" in lower_path or "helper" in lower_path:
            return False

        important_keywords = [
            "service",
            "api",
            "route",
            "model",
            "schema",
            "core",
            "main",
            "repository",
            "dashboard",
            "chat",
            "analysis",
        ]

        return lower_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and any(
            keyword in lower_path for keyword in important_keywords
        )

    def _generate_ai_file_summary(self, path: str, content: str) -> str:
        try:
            from groq import Groq

            if not settings.groq_api_key:
                return ""

            client = Groq(api_key=settings.groq_api_key)
            snippet = content[:2500]

            prompt = f"""
You are a senior software engineer reviewing one source file from a GitHub repository.

File path:
{path}

File content:
{snippet}

Write one useful file insight in 2 short sentences.

Explain:
1. What this file actually does
2. Why it matters in the system

Rules:
- Be specific to the file path and code.
- Do not say generic phrases like "contains logic", "handles functionality", or "implementation file".
- Do not simply count functions/classes/imports.
- Mention responsibility, system role, data flow, or user impact when possible.
- Keep it under 80 words.
- No markdown bullets.
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=160,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You explain source files like a senior engineer. Focus on purpose, responsibility, "
                            "system role, and practical importance."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            summary = (response.choices[0].message.content or "").strip()
            return summary.replace("\n", " ").strip()

        except Exception as exc:
            print(f"AI file summary failed for {path}: {exc}")
            return ""

    def estimate_complexity(self, content: str) -> int:
        control_flow_hits = len(
            re.findall(r"\b(if|for|while|switch|case|except|catch|elif|try)\b", content)
        )
        nesting_penalty = content.count("{") + content.count(":\n")
        function_count = len(
            re.findall(r"^\s*(async\s+def|def|function)\s+\w+", content, re.MULTILINE)
        )

        return min(
            10,
            max(
                1,
                math.ceil((control_flow_hits + nesting_penalty * 0.1 + function_count * 0.25) / 4),
            ),
        )

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
        if "component" in lower_path or lower_path.endswith(".tsx"):
            return "UI component"
        if "config" in lower_path or "settings" in lower_path:
            return "configuration module"

        return "source module"

    def _build_complexity_description(
        self,
        path: str,
        content: str,
        complexity_score: int,
    ) -> str:
        file_name = path.split("/")[-1]
        role = self._infer_file_role(path)
        lower_path = path.lower()

        function_count = len(re.findall(r"^\s*(async\s+def|def)\s+\w+", content, re.MULTILINE))
        class_count = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))
        branch_count = len(re.findall(r"\b(if|for|while|elif|case|except|catch|try)\b", content))
        import_count = len(self._extract_imports(content))

        signals = []

        if function_count >= 8:
            signals.append(f"{function_count} functions suggest several behaviors are grouped together")
        if class_count >= 3:
            signals.append(f"{class_count} classes increase the responsibility scope")
        if branch_count >= 15:
            signals.append(f"{branch_count} branching points make edge cases harder to trace")
        if import_count >= 8:
            signals.append(f"{import_count} dependencies indicate broad coupling")

        if not signals:
            signals.append("multiple decision paths are concentrated in one file")

        signal_text = "; ".join(signals[:3])

        if "test" in lower_path:
            return (
                f"`{file_name}` has a complexity score of {complexity_score}/10. "
                f"Technical signals: {signal_text}. As a test file, this can make failures harder to debug because setup, "
                f"mock data, execution, and assertions may be mixed together. Refactor by moving reusable setup into fixtures, "
                f"separating assertion helpers, and keeping each test focused on one behavior."
            )

        if "model" in lower_path or "schema" in lower_path:
            return (
                f"`{file_name}` has a complexity score of {complexity_score}/10. "
                f"Technical signals: {signal_text}. As a data model, this may tightly couple schemas, validation, and "
                f"transformation rules, causing ripple effects when API or database structures change. Split persistence models, "
                f"request/response schemas, and validation helpers into clearer modules."
            )

        if "service" in lower_path:
            return (
                f"`{file_name}` has a complexity score of {complexity_score}/10. "
                f"Technical signals: {signal_text}. As a service layer file, this likely concentrates business rules and "
                f"orchestration in one place, making feature changes riskier. Extract decision-heavy logic into smaller helpers "
                f"or policy-style modules with focused tests."
            )

        if "util" in lower_path or "helper" in lower_path:
            return (
                f"`{file_name}` has a complexity score of {complexity_score}/10. "
                f"Technical signals: {signal_text}. Utility modules can become hidden dependency hubs when unrelated helpers "
                f"are grouped together. Split helpers by responsibility and move domain-specific helpers closer to the feature "
                f"that owns them."
            )

        if "api" in lower_path or "route" in lower_path:
            return (
                f"`{file_name}` has a complexity score of {complexity_score}/10. "
                f"Technical signals: {signal_text}. API handlers should stay thin, but this file may be mixing request handling, "
                f"validation, business rules, and response formatting. Move core logic into services and keep route handlers focused "
                f"on input/output boundaries."
            )

        return (
            f"`{file_name}` has a complexity score of {complexity_score}/10. "
            f"Technical signals: {signal_text}. As a {role}, this increases cognitive load, slows code review, and raises the "
            f"chance of unintended side effects. Refactor by splitting responsibilities, naming smaller units clearly, and adding "
            f"regression tests before restructuring."
        )

    def detect_risks(self, file_records: list[dict], repo_metadata: dict) -> list[dict]:
        risks: list[dict] = []

        has_readme = any(item["path"].lower().startswith("readme") for item in file_records)
        has_tests = any(item["is_test_file"] for item in file_records)

        if not has_readme:
            risks.append(
                {
                    "title": "Missing README",
                    "severity": "medium",
                    "description": (
                        "The repository does not include a visible README. This slows onboarding because new developers do not "
                        "have a clear setup path, usage example, or explanation of the main entry points."
                    ),
                    "file_path": None,
                }
            )

        if not has_tests:
            risks.append(
                {
                    "title": "Missing test coverage",
                    "severity": "medium",
                    "description": (
                        "No test files were detected in the analyzed subset. This increases regression risk because future changes "
                        "cannot be validated automatically across core workflows."
                    ),
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
                            "description": (
                                f"{description} detected in `{file_name}`. Secrets committed to source code can leak through "
                                f"Git history, logs, forks, or screenshots. Move the value into environment variables or a secret "
                                f"manager and rotate the exposed credential."
                            ),
                            "file_path": path,
                        }
                    )
                    break

            todo_count = len(re.findall(r"\b(TODO|FIXME|HACK)\b", content, flags=re.IGNORECASE))
            if todo_count >= 5:
                risks.append(
                    {
                        "title": "Accumulated technical debt",
                        "severity": "low",
                        "description": (
                            f"`{file_name}` contains {todo_count} TODO/FIXME/HACK markers. This suggests deferred decisions or "
                            f"incomplete implementation details that should be converted into tracked issues or cleaned up before "
                            f"the file becomes harder to maintain."
                        ),
                        "file_path": path,
                    }
                )

            if record["size"] > settings.max_file_bytes * 0.85:
                risks.append(
                    {
                        "title": "Oversized file",
                        "severity": "medium",
                        "description": (
                            f"`{file_name}` is large for a {file_role}. Large files often mix multiple responsibilities, which makes "
                            f"review slower, debugging harder, and ownership less clear. Split the file around clear responsibilities "
                            f"or feature boundaries."
                        ),
                        "file_path": path,
                    }
                )

            if record["complexity_score"] >= 8:
                risks.append(
                    {
                        "title": "High complexity architecture",
                        "severity": "medium",
                        "description": self._build_complexity_description(
                            path=path,
                            content=content,
                            complexity_score=record["complexity_score"],
                        ),
                        "file_path": path,
                    }
                )

        if repo_metadata.get("open_issues_count", 0) > 50:
            risks.append(
                {
                    "title": "High maintenance load",
                    "severity": "low",
                    "description": (
                        "The repository has a high number of open issues, which may indicate unresolved bugs, maintenance pressure, "
                        "or a growing backlog. Review recurring issue themes and prioritize stability or developer-experience improvements."
                    ),
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
                    "title": "Add automated regression coverage",
                    "category": "Testing",
                    "priority": "High",
                    "description": "Add unit and integration tests around the most important workflows before adding more features.",
                    "rationale": (
                        "No strong test presence was detected, so future changes have a higher chance of breaking existing behavior silently."
                    ),
                }
            )

        if not has_readme:
            improvements.append(
                {
                    "title": "Create onboarding documentation",
                    "category": "Documentation",
                    "priority": "High",
                    "description": (
                        "Add a README with project purpose, setup steps, required environment variables, run commands, and example usage."
                    ),
                    "rationale": "Clear onboarding docs reduce setup friction and make the repository easier for new engineers to evaluate.",
                }
            )

        if not has_ci:
            improvements.append(
                {
                    "title": "Add continuous integration checks",
                    "category": "Developer Experience",
                    "priority": "Medium",
                    "description": "Create a CI workflow that runs tests, linting, and basic build validation on every pull request.",
                    "rationale": "Automated validation catches regressions earlier and gives reviewers more confidence in changes.",
                }
            )

        if large_files:
            improvements.append(
                {
                    "title": "Split oversized files by responsibility",
                    "category": "Maintainability",
                    "priority": "Medium",
                    "description": "Break large files into smaller modules organized around features, domain responsibilities, or clear layers.",
                    "rationale": (
                        f"{len(large_files)} large file(s) were detected. Smaller files are easier to review, test, and safely modify."
                    ),
                }
            )

        if complex_files:
            complex_names = ", ".join(item["path"].split("/")[-1] for item in complex_files[:3])
            improvements.append(
                {
                    "title": "Reduce decision-heavy modules",
                    "category": "Code Quality",
                    "priority": "Medium",
                    "description": (
                        "Refactor complex files by extracting repeated branches, isolating business rules, and adding focused tests first."
                    ),
                    "rationale": (
                        f"{len(complex_files)} high-complexity file(s) were detected, including {complex_names}. "
                        f"These files are likely to slow debugging and increase regression risk."
                    ),
                }
            )

        if todo_heavy_files:
            improvements.append(
                {
                    "title": "Convert TODO/FIXME markers into tracked work",
                    "category": "Code Quality",
                    "priority": "Low",
                    "description": "Review TODO/FIXME/HACK markers and either resolve them or convert them into visible backlog items.",
                    "rationale": f"{len(todo_heavy_files)} file(s) contain a high density of unfinished-work markers.",
                }
            )

        if repo_metadata.get("open_issues_count", 0) > 75:
            improvements.append(
                {
                    "title": "Review maintenance backlog",
                    "category": "Project Health",
                    "priority": "Low",
                    "description": "Audit open issues, identify repeated failure themes, and prioritize high-impact cleanup work.",
                    "rationale": "A high open issue count can indicate maintenance pressure or unresolved technical debt.",
                }
            )

        if len(file_records) > 40:
            improvements.append(
                {
                    "title": "Add architecture documentation",
                    "category": "Scalability",
                    "priority": "Medium",
                    "description": "Document main modules, entry points, request/data flow, and ownership boundaries.",
                    "rationale": "Larger repositories are easier to onboard into when system structure is explained explicitly.",
                }
            )

        return improvements[:8]

    def build_repo_summary(
        self,
        repo_metadata: dict,
        file_records: list[dict],
    ) -> RepositorySummaryData:
        self.ai_calls = 0

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
                            "You are a senior software engineer performing a practical architecture review. "
                            "Avoid redundant file listing. Explain purpose, architecture, data flow, and onboarding steps clearly."
                        ),
                    },
                    {"role": "user", "content": prompt},
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
                    f"{repo_name} focuses on {description}. The analyzed implementation files show the main application logic, "
                    f"supporting services, and developer workflow."
                )
            if not architecture:
                architecture = (
                    "The codebase separates implementation logic, configuration, and external interfaces. "
                    "Developers should trace the main entry points first, then follow service-layer calls and data models."
                )
            if not onboarding:
                onboarding = (
                    "Start with the README or main entry point, install dependencies, run the project locally, then review the core "
                    "implementation files before tests and configuration."
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
                f"{repo_name} focuses on {description}. The analyzed implementation files show the main application logic, "
                f"supporting services, and developer workflow."
            )
            architecture = (
                "The codebase separates implementation logic, configuration, and external interfaces. Developers should trace the "
                "main entry points first, then follow service-layer calls and data models."
            )
            onboarding = (
                "Start with the README or main entry point, install dependencies, run the project locally, then review the core "
                "implementation files before tests and configuration."
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

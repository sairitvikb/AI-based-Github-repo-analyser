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
        self.max_ai_calls = 8

    def summarize_file(self, path: str, content: str) -> str:
        language = infer_language_from_path(path) or "text"
        lower_path = path.lower()

        if not content.strip():
            return "Empty file with no meaningful implementation content."

        if self._should_use_ai_file_summary(lower_path, content) and self.ai_calls < self.max_ai_calls:
            self.ai_calls += 1
            ai_summary = self._generate_ai_file_summary(path, content)
            if ai_summary:
                return ai_summary

        return self._smart_fallback_summary(path, content, language)

    def _smart_fallback_summary(self, path: str, content: str, language: str) -> str:
        lower_path = path.lower()
        filename = path.split("/")[-1]

        functions = re.findall(r"^\s*(?:async\s+def|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE)
        classes = re.findall(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE)
        imports = self._extract_imports(content)
        assertions = len(re.findall(r"\bassert\b", content))
        branches = len(re.findall(r"\b(if|elif|else|for|while|try|except|case|catch)\b", content))
        fixtures = re.findall(r"@pytest\.fixture\s*\n\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)", content)
        test_names = re.findall(r"def\s+(test_[a-zA-Z0-9_]+)", content)

        if lower_path.endswith(".md"):
            heading = self._first_heading(content)
            return (
                f"`{filename}` documents {heading or 'project usage and developer context'}. "
                f"It helps new contributors understand setup, behavior, or design decisions without reading source code first."
            )

        if lower_path.endswith((".yml", ".yaml")):
            if ".github/workflows/" in lower_path:
                return (
                    f"`{filename}` defines automation for repository quality checks such as builds, tests, or deployment steps. "
                    f"It improves reliability by making validation repeatable instead of depending on manual developer actions."
                )
            return (
                f"`{filename}` stores structured configuration used by tooling or runtime setup. "
                f"It matters because small config changes can affect how the project builds, runs, or deploys."
            )

        if lower_path.endswith(".json"):
            if filename == "package.json":
                scripts = re.findall(r'"([^"]+)"\s*:', content)
                useful_scripts = [s for s in scripts if s in {"dev", "build", "test", "lint", "start"}]
                script_text = ", ".join(useful_scripts[:4]) if useful_scripts else "project scripts"
                return (
                    f"`package.json` defines frontend/tooling dependencies and scripts such as {script_text}. "
                    f"It is the main entry point for installing, running, building, and validating the JavaScript side of the project."
                )
            return (
                f"`{filename}` contains structured project metadata or configuration. "
                f"It supports predictable tooling behavior by keeping settings machine-readable."
            )

        if lower_path.endswith(".py"):
            if "conftest.py" in lower_path:
                return (
                    f"`{filename}` configures shared pytest behavior for the test suite. "
                    f"It usually provides reusable fixtures, test setup, or dependency overrides so individual tests stay cleaner."
                )

            if "test" in lower_path:
                readable_tests = [
                    name.replace("test_", "").replace("_", " ")
                    for name in test_names[:3]
                ]

                if fixtures:
                    detail = f"uses fixtures like {', '.join(fixtures[:3])}"
                elif readable_tests:
                    detail = f"covers scenarios such as {', '.join(readable_tests)}"
                elif assertions:
                    detail = f"contains {assertions} assertion checks"
                else:
                    detail = "adds regression checks for related behavior"

                complexity_note = (
                    " Because this file has noticeable branching, separating setup from assertions would make failures easier to debug."
                    if branches >= 8
                    else " This keeps the related feature safer when future changes are made."
                )

                tested_area = filename.replace("test_", "").replace("_test", "").replace(".py", "")
                tested_area = tested_area.replace("_", " ").strip() or "related functionality"

                return (
                    f"`{filename}` validates {tested_area} and {detail}. "
                    f"It protects behavior that could otherwise break silently during refactoring.{complexity_note}"
                )

            if "model" in lower_path or "schema" in lower_path:
                named = ", ".join(classes[:3]) if classes else "data objects"
                return (
                    f"`{filename}` defines data contracts such as {named}. "
                    f"It matters because these structures shape validation, persistence, and API response behavior across the backend."
                )

            if "service" in lower_path:
                main_funcs = ", ".join(functions[:3]) if functions else "service operations"
                return (
                    f"`{filename}` coordinates backend workflow through {main_funcs}. "
                    f"It is important because service files usually hold business rules, orchestration, and calls between data and API layers."
                )

            if "api" in lower_path or "route" in lower_path:
                endpoints = re.findall(r"@\w+\.(get|post|put|delete|patch)\(", content)
                endpoint_text = f"{len(endpoints)} route handler pattern(s)" if endpoints else "request handlers"
                return (
                    f"`{filename}` exposes backend functionality through {endpoint_text}. "
                    f"It connects client requests to validation, service logic, and response formatting."
                )

            if "config" in lower_path or "settings" in lower_path:
                return (
                    f"`{filename}` centralizes runtime configuration and environment-driven settings. "
                    f"It matters because deployment, API keys, database URLs, and feature behavior should be controlled outside hardcoded logic."
                )

            if "parser" in lower_path:
                return (
                    f"`{filename}` converts raw input into structured data the application can trust. "
                    f"This reduces downstream complexity because later services can operate on normalized values instead of messy input."
                )

            if "exception" in lower_path:
                return (
                    f"`{filename}` defines custom error types for predictable failure handling. "
                    f"It helps the backend communicate failures consistently instead of scattering generic exceptions across the codebase."
                )

            if "util" in lower_path or "helper" in lower_path:
                main_funcs = ", ".join(functions[:4]) if functions else "shared helper routines"
                return (
                    f"`{filename}` provides reusable helper behavior through {main_funcs}. "
                    f"It should stay focused because utility files can easily become hidden dependency hubs used across unrelated features."
                )

            named_items = []
            if classes:
                named_items.append(f"classes like {', '.join(classes[:2])}")
            if functions:
                named_items.append(f"functions like {', '.join(functions[:3])}")
            if imports:
                named_items.append(f"dependencies such as {', '.join(imports[:3])}")

            detail = "; ".join(named_items) if named_items else "module-level Python behavior"
            return (
                f"`{filename}` implements {detail}. "
                f"It contributes to the repository by grouping related Python behavior that other modules can import and reuse."
            )

        if lower_path.endswith((".ts", ".tsx", ".js", ".jsx")):
            components = re.findall(r"(?:function|const)\s+([A-Z][A-Za-z0-9_]*)", content)
            hooks = re.findall(r"(use[A-Z][A-Za-z0-9_]*)", content)
            api_calls = re.findall(r"\b(fetch|axios\.[a-z]+)\b", content)

            if lower_path.endswith(".tsx") or "component" in lower_path:
                component_name = components[0] if components else filename
                return (
                    f"`{filename}` renders the `{component_name}` UI experience. "
                    f"It matters because this component controls what users see, how state is presented, and how repository analysis results become understandable."
                )

            if "service" in lower_path or "api" in lower_path:
                return (
                    f"`{filename}` manages client-side communication with backend endpoints. "
                    f"It keeps network requests separate from UI components, making the frontend easier to maintain and test."
                )

            if "hook" in lower_path or hooks:
                hook_name = hooks[0] if hooks else "shared hook behavior"
                return (
                    f"`{filename}` provides reusable React logic through {hook_name}. "
                    f"It helps avoid duplicated state or side-effect handling across multiple components."
                )

            if "type" in lower_path:
                return (
                    f"`{filename}` defines TypeScript contracts used by the frontend. "
                    f"It reduces integration bugs by making API response shapes and UI data structures explicit."
                )

            return (
                f"`{filename}` contains JavaScript/TypeScript application behavior. "
                f"It supports the frontend by organizing state, rendering logic, or browser-side workflow code."
            )

        if lower_path.endswith(".css"):
            return (
                f"`{filename}` controls visual styling such as layout, spacing, colors, and responsive behavior. "
                f"It affects product polish because styling determines how clearly users can read and navigate the interface."
            )

        if lower_path.endswith(".html"):
            return (
                f"`{filename}` defines the base HTML shell for the app. "
                f"It provides the mounting structure where frontend JavaScript renders the user interface."
            )

        return (
            f"`{filename}` is a {language} file used by the repository. "
            f"It likely supports configuration, implementation, or supporting project behavior."
        )

    def _should_use_ai_file_summary(self, lower_path: str, content: str) -> bool:
        if not settings.groq_api_key:
            return False

        if len(content.strip()) < 700:
            return False

        if lower_path.endswith((".md", ".yml", ".yaml", ".json", ".lock", ".txt", ".css", ".html")):
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

            client = Groq(api_key=settings.groq_api_key)
            snippet = content[:2800]

            prompt = f"""
You are a senior engineer reviewing one file.

File path:
{path}

File content:
{snippet}

Write exactly 2 sentences.
Sentence 1: explain what this file specifically does.
Sentence 2: explain why it matters or what risk/improvement a developer should know.

Avoid generic words like "handles", "contains", "functionality", "various", "logic".
Use specific nouns from the code.
No markdown.
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.25,
                max_tokens=140,
                messages=[
                    {
                        "role": "system",
                        "content": "You write practical code-review style file insights. Be specific and concise.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            return (response.choices[0].message.content or "").replace("\n", " ").strip()

        except Exception:
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

    def _build_complexity_description(self, path: str, content: str, complexity_score: int) -> str:
        file_name = path.split("/")[-1]
        role = self._infer_file_role(path)
        lower_path = path.lower()

        function_count = len(re.findall(r"^\s*(async\s+def|def)\s+\w+", content, re.MULTILINE))
        class_count = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))
        branch_count = len(re.findall(r"\b(if|for|while|elif|case|except|catch|try)\b", content))
        import_count = len(self._extract_imports(content))

        signals = []

        if function_count >= 8:
            signals.append(f"{function_count} functions grouped together")
        if class_count >= 3:
            signals.append(f"{class_count} classes in one file")
        if branch_count >= 15:
            signals.append(f"{branch_count} branching points")
        if import_count >= 8:
            signals.append(f"{import_count} dependencies")

        if not signals:
            signals.append("several decision paths concentrated in one file")

        signal_text = "; ".join(signals[:3])

        if "test" in lower_path:
            return (
                f"`{file_name}` scores {complexity_score}/10 because it has {signal_text}. "
                f"For a test file, this can hide whether failures come from setup, mocks, execution, or assertions. "
                f"Split shared setup into fixtures and keep each test focused on one behavior."
            )

        if "model" in lower_path or "schema" in lower_path:
            return (
                f"`{file_name}` scores {complexity_score}/10 because it has {signal_text}. "
                f"For a data model file, this can tightly couple validation, schema shape, and API/database contracts. "
                f"Separate persistence models, request schemas, response schemas, and validation helpers."
            )

        if "service" in lower_path:
            return (
                f"`{file_name}` scores {complexity_score}/10 because it has {signal_text}. "
                f"For a service layer file, this can concentrate business rules and make feature changes risky. "
                f"Extract decision-heavy branches into smaller policy/helper functions with tests."
            )

        if "api" in lower_path or "route" in lower_path:
            return (
                f"`{file_name}` scores {complexity_score}/10 because it has {signal_text}. "
                f"API handlers should stay thin, so this may be mixing routing, validation, business rules, and response shaping. "
                f"Move core behavior into services and keep routes focused on request/response boundaries."
            )

        return (
            f"`{file_name}` scores {complexity_score}/10 because it has {signal_text}. "
            f"As a {role}, this increases cognitive load and makes safe refactoring harder. "
            f"Split responsibilities into smaller named units and protect behavior with regression tests."
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
                    "description": "The repository lacks visible onboarding documentation, making setup and contribution harder for new developers.",
                    "file_path": None,
                }
            )

        if not has_tests:
            risks.append(
                {
                    "title": "Missing test coverage",
                    "severity": "medium",
                    "description": "No test files were detected, which increases regression risk when future changes are made.",
                    "file_path": None,
                }
            )

        for record in file_records:
            content = record["content"]
            path = record["path"]
            file_name = path.split("/")[-1]

            for pattern, description in SECRET_PATTERNS:
                if pattern.search(content):
                    risks.append(
                        {
                            "title": "Potential hardcoded secret",
                            "severity": "high",
                            "description": f"{description} detected in `{file_name}`. Move it to environment variables or a secret manager and rotate the exposed value.",
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
                        "description": f"`{file_name}` contains {todo_count} unfinished-work markers, suggesting deferred decisions that should be tracked or cleaned up.",
                        "file_path": path,
                    }
                )

            if record["size"] > settings.max_file_bytes * 0.85:
                risks.append(
                    {
                        "title": "Oversized file",
                        "severity": "medium",
                        "description": f"`{file_name}` is large for a {self._infer_file_role(path)}, which can slow review and make ownership unclear.",
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

        return risks[:20]

    def suggest_improvements(self, file_records: list[dict], repo_metadata: dict) -> list[dict]:
        improvements: list[dict] = []

        has_readme = any(item["path"].lower().startswith("readme") for item in file_records)
        has_tests = any(item["is_test_file"] for item in file_records)
        has_ci = any(
            ".github/workflows/" in item["path"].lower() or "gitlab-ci" in item["path"].lower()
            for item in file_records
        )

        complex_files = [item for item in file_records if item["complexity_score"] >= 8]
        large_files = [item for item in file_records if item["size"] > 80000]

        if not has_tests:
            improvements.append(
                {
                    "title": "Add automated regression coverage",
                    "category": "Testing",
                    "priority": "High",
                    "description": "Add unit and integration tests around the most important workflows.",
                    "rationale": "Without tests, future changes can break existing behavior silently.",
                }
            )

        if not has_readme:
            improvements.append(
                {
                    "title": "Create onboarding documentation",
                    "category": "Documentation",
                    "priority": "High",
                    "description": "Add a README with setup steps, environment variables, run commands, and usage examples.",
                    "rationale": "Clear docs reduce setup friction for new contributors.",
                }
            )

        if not has_ci:
            improvements.append(
                {
                    "title": "Add continuous integration checks",
                    "category": "Developer Experience",
                    "priority": "Medium",
                    "description": "Run tests, linting, and build validation automatically on pull requests.",
                    "rationale": "CI catches regressions earlier and improves reviewer confidence.",
                }
            )

        if complex_files:
            names = ", ".join(item["path"].split("/")[-1] for item in complex_files[:3])
            improvements.append(
                {
                    "title": "Reduce decision-heavy modules",
                    "category": "Code Quality",
                    "priority": "Medium",
                    "description": "Extract repeated branches, isolate business rules, and add focused tests before refactoring.",
                    "rationale": f"{len(complex_files)} high-complexity file(s) were detected, including {names}.",
                }
            )

        if large_files:
            improvements.append(
                {
                    "title": "Split oversized files by responsibility",
                    "category": "Maintainability",
                    "priority": "Medium",
                    "description": "Break large files into smaller modules organized around features or layers.",
                    "rationale": f"{len(large_files)} large file(s) were detected.",
                }
            )

        return improvements[:8]

    def build_repo_summary(self, repo_metadata: dict, file_records: list[dict]) -> RepositorySummaryData:
        self.ai_calls = 0

        languages = Counter([record["language"] or "Unknown" for record in file_records])
        likely_stack = [language for language, _ in languages.most_common(6)]

        important_records = [
            item
            for item in file_records
            if not item["is_test_file"]
            and not item["path"].lower().endswith((".md", ".yml", ".yaml", ".json", ".txt", ".lock"))
        ]

        selected_records = important_records[:25] if important_records else file_records[:25]
        top_files = "\n".join([f"- {item['path']}: {item['summary']}" for item in selected_records])

        repo_name = repo_metadata.get("name", "repository")
        description = repo_metadata.get("description") or "No description provided."

        prompt = f"""
You are a senior software engineer performing a practical architecture review.

Repository Name:
{repo_name}

GitHub Description:
{description}

Likely Technologies:
{", ".join(likely_stack)}

Important Files:
{top_files}

Return exactly:

1. Concise Summary
<2 lines max>

2. Detailed Summary
<3-4 useful sentences>

3. Architecture Summary
<3 lines max>

4. Developer Onboarding Summary
<3 lines max>
"""

        try:
            from groq import Groq

            if not settings.groq_api_key:
                raise ValueError("Missing GROQ_API_KEY")

            client = Groq(api_key=settings.groq_api_key)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.15,
                max_tokens=700,
                messages=[
                    {
                        "role": "system",
                        "content": "Explain repository purpose, architecture, data flow, and onboarding clearly.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            text = (response.choices[0].message.content or "").strip()

            concise = self._extract_section(text, "1. Concise Summary", "2. Detailed Summary")
            detailed = self._extract_section(text, "2. Detailed Summary", "3. Architecture Summary")
            architecture = self._extract_section(text, "3. Architecture Summary", "4. Developer Onboarding Summary")
            onboarding = self._extract_section(text, "4. Developer Onboarding Summary", None)

            return RepositorySummaryData(
                concise_summary=concise or f"{repo_name} is built using {', '.join(likely_stack[:3])}.",
                detailed_summary=detailed or f"{repo_name} focuses on {description}.",
                architecture_summary=architecture or "The repository separates configuration, implementation logic, and external interfaces.",
                onboarding_summary=onboarding or "Start with the README, install dependencies, run the app, then inspect core modules.",
                likely_stack=likely_stack,
            )

        except Exception as exc:
            print(f"Groq summary generation failed: {exc}")

            return RepositorySummaryData(
                concise_summary=f"{repo_name} is built using {', '.join(likely_stack[:3])}.",
                detailed_summary=f"{repo_name} focuses on {description}. The analyzed files show the main implementation and developer workflow.",
                architecture_summary="The repository separates configuration, implementation logic, and external interfaces.",
                onboarding_summary="Start with the README, install dependencies, run the app, then inspect core modules.",
                likely_stack=likely_stack,
            )

    def _extract_imports(self, content: str) -> list[str]:
        imports = set()

        for match in re.findall(r"^\s*import\s+([\w\.]+)", content, flags=re.MULTILINE):
            imports.add(match.split(".")[0])

        for match in re.findall(r"^\s*from\s+([\w\.]+)\s+import", content, flags=re.MULTILINE):
            imports.add(match.split(".")[0])

        for match in re.findall(r'require\(["\']([^"\']+)["\']\)', content):
            imports.add(match.split("/")[0])

        return sorted(imports)

    def _first_heading(self, content: str) -> str:
        for line in content.splitlines():
            if line.strip().startswith("#"):
                return line.strip().lstrip("#").strip()
        return ""

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
            section = text[start_index:] if end_index == -1 else text[start_index:end_index]

        return section.strip()

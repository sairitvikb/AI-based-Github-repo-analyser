from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".jsx": "JSX",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
}

IGNORED_PARTS = {
    "node_modules",
    "dist",
    "build",
    ".next",
    ".git",
    "coverage",
    "venv",
    ".venv",
    ".github",
    ".devcontainer",
    "docs",
    "doc",
    "examples",
    "example",
    "__pycache__",
}

IGNORED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}

LOW_SIGNAL_PATH_PARTS = {
    "tests",
    "test",
    "spec",
    "fixtures",
    "migrations",
    "static",
    "templates",
}

HIGH_SIGNAL_PATH_PARTS = {
    "src",
    "app",
    "api",
    "core",
    "services",
    "server",
    "backend",
    "frontend",
    "lib",
    "langchain",
}

HIGH_SIGNAL_FILENAMES = {
    "main.py",
    "app.py",
    "server.py",
    "index.ts",
    "index.js",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile",
    "README.md",
}


def infer_language_from_path(path: str) -> str | None:
    return SUPPORTED_EXTENSIONS.get(Path(path).suffix.lower())


def is_supported_source_file(path: str) -> bool:
    path_obj = Path(path)
    parts = set(path_obj.parts)
    filename = path_obj.name

    if parts.intersection(IGNORED_PARTS):
        return False
    if filename in IGNORED_FILENAMES:
        return False

    return path_obj.suffix.lower() in SUPPORTED_EXTENSIONS


def is_low_signal_file(path: str) -> bool:
    path_obj = Path(path)
    parts = {part.lower() for part in path_obj.parts}
    return bool(parts.intersection(LOW_SIGNAL_PATH_PARTS))


def get_file_priority(path: str) -> int:
    path_obj = Path(path)
    parts = {part.lower() for part in path_obj.parts}
    filename = path_obj.name

    score = 0

    if filename in HIGH_SIGNAL_FILENAMES:
        score += 6

    if parts.intersection(HIGH_SIGNAL_PATH_PARTS):
        score += 4

    if is_low_signal_file(path):
        score -= 3

    suffix = path_obj.suffix.lower()
    if suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go"}:
        score += 2
    elif suffix in { ".json", ".yaml", ".yml"}:
        score += 1
    elif suffix == ".md":
        score -= 2

    return score
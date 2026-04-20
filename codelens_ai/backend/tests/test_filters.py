from app.utils.repository_filters import infer_language_from_path, is_supported_source_file


def test_infer_language_from_path() -> None:
    assert infer_language_from_path("src/main.py") == "Python"


def test_ignore_node_modules() -> None:
    assert is_supported_source_file("node_modules/react/index.js") is False

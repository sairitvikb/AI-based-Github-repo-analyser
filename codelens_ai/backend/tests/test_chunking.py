from app.utils.chunking import chunk_text


def test_chunk_text_splits_large_input() -> None:
    text = "a" * 3000
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100)
    assert len(chunks) >= 3
    assert chunks[0] == "a" * 1000

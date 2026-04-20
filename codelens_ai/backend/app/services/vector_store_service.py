from __future__ import annotations

from uuid import uuid4

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import settings


class VectorStoreService:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)

    def get_collection(self, repo_id: int) -> Collection:
        return self.client.get_or_create_collection(name=f"repo_{repo_id}")

    def reset_collection(self, repo_id: int) -> None:
        name = f"repo_{repo_id}"
        try:
            self.client.delete_collection(name=name)
        except Exception:
            pass

    def upsert_chunks(self, repo_id: int, chunks: list[dict]) -> None:
        if not chunks:
            return

        collection = self.get_collection(repo_id)
        ids = [str(uuid4()) for _ in chunks]
        collection.upsert(
            ids=ids,
            documents=[chunk["content"] for chunk in chunks],
            metadatas=[
                {
                    "file_path": chunk["path"],
                    "priority": chunk.get("priority", 0),
                }
                for chunk in chunks
            ],
        )

    def search(self, repo_id: int, query: str, limit: int = 12) -> list[dict]:
        collection = self.get_collection(repo_id)
        results = collection.query(query_texts=[query], n_results=limit)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        ranked = []
        for doc, metadata in zip(documents, metadatas, strict=False):
            ranked.append(
                {
                    "content": doc,
                    "file_path": metadata.get("file_path", "unknown"),
                    "priority": metadata.get("priority", 0),
                }
            )

        return ranked
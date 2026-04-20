from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class ChatSource(BaseModel):
    file_path: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]

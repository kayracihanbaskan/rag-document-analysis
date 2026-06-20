from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks: int


class SearchHit(BaseModel):
    text: str
    page_number: int | None
    document_id: str
    score: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit] = Field(default_factory=list)


class ChatRequest(BaseModel):
    question: str
    document_id: str | None = None
    top_k: int = 5


class ChatSource(BaseModel):
    text: str
    page_number: int | None
    document_id: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    recipe_id: str
    content: str
    score: float = Field(ge=0.0, le=1.0)


class RagQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class RagQuestionResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = Field(default_factory=list)


class RagContext(BaseModel):
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)

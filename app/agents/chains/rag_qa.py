from app.agents.router import AgentRouter
from app.rag.retriever import RecipeRetriever
from app.rag.schemas import RagQuestionResponse


async def answer_with_rag(question: str) -> RagQuestionResponse:
    retriever = RecipeRetriever()
    chunks = retriever.retrieve(question)
    if not chunks:
        return RagQuestionResponse(
            question=question,
            answer="I couldn't find relevant recipe context yet. Try again after recipes are indexed.",
            sources=[],
        )

    router = AgentRouter()
    context = "\n\n".join(chunk.content for chunk in chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {question}"
    answer = await router.route("rag_qa", prompt)
    return RagQuestionResponse(
        question=question,
        answer=answer or "No answer generated.",
        sources=[chunk.content for chunk in chunks],
    )

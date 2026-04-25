from fastapi import APIRouter, HTTPException, status

from backend.modules.llm import service
from backend.schemas.llm import GeneratePostRequest, GeneratePostResponse

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/generate", response_model=GeneratePostResponse)
def generate_post(payload: GeneratePostRequest) -> GeneratePostResponse:
    try:
        text, model, shots_used = service.generate_post_text(query=payload.query)
    except service.LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM error: {e}",
        )

    return GeneratePostResponse(text=text, model=model, shots_used=shots_used)

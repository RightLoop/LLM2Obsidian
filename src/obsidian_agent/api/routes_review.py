"""Review routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.schemas import GenerateReviewRequest

router = APIRouter(prefix="/review", tags=["review"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.post("/generate")
async def generate_review(
    request: GenerateReviewRequest, container: ContainerDep
) -> dict[str, object]:
    related_notes = await container.retrieval_service.find_related_notes(
        request.note_path,
        top_k=request.top_k,
    )
    return await container.synthesis_workflow.run(request.note_path, related_notes)


@router.get("/pending")
async def pending(container: ContainerDep) -> dict[str, object]:
    return {"items": await container.review_service.list_pending()}


@router.post("/{review_id}/approve")
async def approve(review_id: int, container: ContainerDep) -> dict[str, str]:
    await container.review_service.approve(review_id)
    return {"status": "approved"}


@router.post("/{review_id}/reject")
async def reject(review_id: int, container: ContainerDep) -> dict[str, str]:
    await container.review_service.reject(review_id)
    return {"status": "rejected"}


@router.post("/{review_id}/apply")
async def apply(review_id: int, container: ContainerDep) -> dict[str, str]:
    await container.review_service.apply_approved_review(review_id)
    return {"status": "applied"}

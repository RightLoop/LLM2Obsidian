"""Review routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from obsidian_agent.api.deps import get_api_container

router = APIRouter(prefix="/review", tags=["review"])
ContainerDep = Annotated[object, Depends(get_api_container)]


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

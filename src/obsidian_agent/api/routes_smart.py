"""Smart knowledge routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.schemas import (
    ErrorCaptureRequest,
    NodePackRequest,
    TeachingPackRequest,
)

router = APIRouter(prefix="/smart", tags=["smart"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.post("/error-capture")
async def smart_error_capture(
    request: ErrorCaptureRequest,
    container: ContainerDep,
) -> dict[str, object]:
    response = await container.smart_capture_service.capture_error(request)
    return response.model_dump(mode="json")


@router.post("/node-pack")
async def smart_node_pack(
    request: NodePackRequest,
    container: ContainerDep,
) -> dict[str, object]:
    try:
        response = await container.smart_node_pack_service.build_node_pack(
            node_key=request.node_key,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.post("/teach")
async def smart_teach(
    request: TeachingPackRequest,
    container: ContainerDep,
) -> dict[str, object]:
    try:
        response = await container.teaching_planner_service.build_teaching_pack(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return response.model_dump(mode="json")


@router.get("/related-nodes")
async def smart_related_nodes(
    node_key: str = Query(min_length=3),
    top_k: int = Query(default=5, ge=1, le=10),
    container: object = Depends(get_api_container),
) -> dict[str, object]:
    try:
        items = await container.smart_query_service.related_nodes(node_key=node_key, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"node_key": node_key, "items": [item.model_dump(mode="json") for item in items]}

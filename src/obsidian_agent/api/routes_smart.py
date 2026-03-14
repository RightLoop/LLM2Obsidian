"""Smart knowledge routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from obsidian_agent.api.deps import get_api_container
from fastapi import HTTPException, status

from obsidian_agent.domain.schemas import ErrorCaptureRequest, NodePackRequest

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

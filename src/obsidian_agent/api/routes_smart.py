"""Smart knowledge routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.schemas import ErrorCaptureRequest

router = APIRouter(prefix="/smart", tags=["smart"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.post("/error-capture")
async def smart_error_capture(
    request: ErrorCaptureRequest,
    container: ContainerDep,
) -> dict[str, object]:
    response = await container.smart_capture_service.capture_error(request)
    return response.model_dump(mode="json")

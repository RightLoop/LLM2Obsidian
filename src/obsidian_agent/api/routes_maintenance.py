"""Maintenance routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from obsidian_agent.api.deps import get_api_container
from obsidian_agent.domain.schemas import WeeklyDigestRequest

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
ContainerDep = Annotated[object, Depends(get_api_container)]


@router.post("/reindex")
async def reindex(container: ContainerDep) -> dict[str, object]:
    paths = await container.indexing_service.reindex_all()
    return {"count": len(paths), "paths": paths}


@router.get("/orphans")
async def orphans(container: ContainerDep) -> dict[str, object]:
    items = await container.maintenance_service.find_orphan_notes()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/duplicates")
async def duplicates(container: ContainerDep) -> dict[str, object]:
    items = await container.maintenance_service.find_duplicate_candidates()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/metadata-issues")
async def metadata_issues(container: ContainerDep) -> dict[str, object]:
    items = await container.maintenance_service.find_metadata_issues()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.post("/weekly-digest")
async def weekly_digest(
    request: WeeklyDigestRequest, container: ContainerDep
) -> dict[str, object]:
    path = await container.maintenance_workflow.weekly_digest(request.week_key)
    return {"path": path}
